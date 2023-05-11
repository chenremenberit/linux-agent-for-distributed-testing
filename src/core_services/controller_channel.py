import threading
import queue

from common.message_format import MessageFormatEnum
from common.mqtt_enum import MQTTServerEnum
from common.websocket_enum import WebsocketEnum
from core_services.mqtt_channel import MQTTChannel
from core_services.websocket_channel import WebSocketChannel
from util.logger_manager_ment import Logger


class ControllerChannel:
    def __init__(self, device_id):
        '''
        channel类，主机代理
        :return:
        '''
        self.device_id = device_id
        self.protocol_type_dict = {"MQTT": {"class": "MQTTChannel",
                                            "host": MQTTServerEnum.MQTT_SERVER_HOST.value,
                                            "port": MQTTServerEnum.MQTT_SERVER_PORT.value,
                                            "device_id": device_id},
                                   "WebSocket": {"class": "WebSocketChannel",
                                                 "host": WebsocketEnum.WEBSOCKET_HOST.value,
                                                 "port": WebsocketEnum.WEBSOCKET_PORT.value,
                                                 "device_id": device_id}}
        self.channel_function_dict = {"MQTT": {"send_message_func_name": "publish_message_to_mqtt_server",
                                               "receive_message_func_name": "subscriber_connect_to_mqtt_server",
                                               "message_queue": "mqtt_message_queue"},
                                      "WebSocket": {"send_message_func_name": "asyncio_run_send_message_to_websocket_server",
                                                    "receive_message_func_name": "asyncio_run_receive_message_from_websocket_server",
                                                    "message_queue": "websocket_message_queue"}}
        self.logger = Logger("Channel")
        self.message_queue = queue.Queue()

    def send_message_to_server(self, protocol_type, command, receiver_device_id):
        '''
        channel发送信息
        :return:
        '''
        if protocol_type not in self.protocol_type_dict:
            return self.logger.error("Unknown protocol_type")
        channel_class_info = self.protocol_type_dict[protocol_type]
        channel_class = globals()[channel_class_info["class"]]
        kwargs = {key: var for key, var in channel_class_info.items() if key != 'class'}
        channel = channel_class(**kwargs)
        send_message = getattr(channel, self.channel_function_dict[protocol_type]['send_message_func_name'])
        return send_message(command, receiver_device_id)

    def get_message_from_server(self, protocol_type):
        '''
        channel接收消息
        :return:
        '''
        if protocol_type not in self.protocol_type_dict:
            return self.logger.error("Unknown protocol_type")
        channel_class_info = self.protocol_type_dict[protocol_type]
        channel_class = globals()[channel_class_info["class"]]
        kwargs = {key: var for key, var in channel_class_info.items() if key != "class"}
        channel = channel_class(**kwargs)
        receive_message = getattr(channel, self.channel_function_dict[protocol_type]["receive_message_func_name"])
        channel_message_queue_name = self.channel_function_dict[protocol_type]["message_queue"]
        if channel_message_queue_name:
            channel_message_queue = getattr(channel, channel_message_queue_name)
            message = channel_message_queue.get()
            self.message_queue.put(message)
        return receive_message()

    def launch_get_message_threads(self):
        '''
        拉起获取信息get_message_from_server的线程
        '''
        for protocol_type in self.channel_function_dict.keys():
            get_message_from_server_threading = threading.Thread(target=self.get_message_from_server, args=(protocol_type,))
            get_message_from_server_threading.start()

    def reply_to_server(self):
        '''
        根据获取信息的queue来回复服务器
        '''
        while True:
            message = self.message_queue.get()
            message_list = message.splitlines()
            received_element_list = [content.split(": ", maxsplit=1)[1] for content in message_list]
            protocol = received_element_list[MessageFormatEnum.RECEIVING_PROTOCOL_POSITION.value]
            command = received_element_list[MessageFormatEnum.RECEIVING_COMMAND_POSITION.value]
            receiver = received_element_list[MessageFormatEnum.RECEIVING_RECEIVER_POSITION.value]
            self.send_message_to_server(protocol, command, receiver)


if __name__ == "__main__":
    mqtt = ControllerChannel("A")
    mqtt.launch_get_message_threads()
    mqtt.reply_to_server()
    
    # mqtt.get_message_from_device("MQTT")
