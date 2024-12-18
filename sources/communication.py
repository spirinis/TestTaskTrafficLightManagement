class Communication:
    """Класс для передачи сообщений между объектами. В реальных условиях для общения 12 устройств заменяется
    на кодирование, передачу p2p по протоколу транспортного уровня и декодирование"""
    ALL_TRAFFIC_LIGHTS = {}  # id: TrafficLight

    @classmethod
    def send(cls, target_id: str | int, message: dict):
        cls.ALL_TRAFFIC_LIGHTS.get(target_id).message_queue_add(message)
