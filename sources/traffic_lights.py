import time
import threading
from sources.communication import Communication
import sources.constants as constants


class TrafficLight:
    busy_ids = []
    _POSSIBLE_STATES = ()

    def __init__(self, id_: int | str, working_group: tuple) -> None:
        if id_ not in self.busy_ids:
            self.__id = id_
            self.busy_ids.append(id_)
        else:
            raise ValueError(f"id {id_} уже занято")
        self.__monitored_queue_size = 0
        self.__message_queue = []
        self.__state = constants.RED  # Начальное состояние
        self.__working_group = working_group

    @property
    def id(self) -> int | str:
        return self.__id

    @property
    def monitored_queue_size(self) -> int:
        return self.__monitored_queue_size

    @monitored_queue_size.setter
    def monitored_queue_size(self, value):
        self.__monitored_queue_size = value

    def monitored_queue_size_add(self, value: int) -> None:
        self.__monitored_queue_size += value
        message = {'id': self.id, 'do': 'change_monitored_queue', 'change': value}
        self.send_message_to_all(message, to_all=False)

    @property
    def message_queue(self):
        return self.__message_queue

    def message_queue_add(self, message: dict) -> None:
        self.__message_queue.append(message)
        self.do()

    @property
    def state(self) -> str:
        return self.__state

    @state.setter
    def state(self, value) -> None:
        if value in self._POSSIBLE_STATES:
            self.__state = value
        else:
            raise ValueError(f'\'{value}\' не может быть состоянием')

    @property
    def working_group(self):
        return self.__working_group

    def message_queue_get(self) -> dict:
        return self.__message_queue.pop(0)

    def send_message_to_all(self, message: dict, to_all: bool = True, is_informative: bool = True) -> None:
        if is_informative:
            print(f'{self.id} отправил {message}')
        for traffic_light_id in (self.busy_ids if to_all else self.busy_ids[:4]):
            if traffic_light_id != self.id:
                Communication.send(traffic_light_id, message)

    def do(self):
        pass


class PedestrianTrafficLight(TrafficLight):
    _POSSIBLE_STATES = (constants.RED, constants.GREEN)

    def __init__(self, id_: int | str, working_group: tuple) -> None:
        super().__init__(id_, working_group)

    def __repr__(self) -> str:
        return f'PedestrianTrafficLight({self.id}, {self.state})'

    def do(self):
        message = self.message_queue_get()
        if 'do' in message:
            id_ = message.get('id')
            do_what = message.get('do')
            if do_what == 'change_state':
                leader_id = message.get('leader')
                if leader_id == id_:
                    leader_state = message.get('state')
                    if id_ in self.working_group:
                        if leader_state == constants.RED:
                            self.change_state(constants.RED, leader_id)
                        elif leader_state == constants.GREEN:
                            self.change_state(constants.GREEN, leader_id)
                        elif leader_state == constants.YELLOW:
                            self.change_state(constants.RED, leader_id)
                    else:
                        self.change_state(constants.RED, leader_id)

    def change_state(self, state: str, leader: int | str) -> None:
        is_informative = False
        if self.state != state:
            self.state = state
            is_informative = True
        message = {'id': self.id, 'leader': leader, 'do': 'change_state', 'state': self.state}
        self.send_message_to_all(message, is_informative=is_informative)


class CarTrafficLight(TrafficLight):
    _POSSIBLE_STATES = (constants.RED, constants.YELLOW, constants.GREEN)

    def __init__(self, id_: int | str, working_group: tuple) -> None:
        super().__init__(id_, working_group)
        self.previous_state = constants.GREEN
        self.yellow_thread = None
        self.expectant_thread = None
        self.__monitored_group_queue_size = 0
        self.__other_monitored_group_queues = {}
        self.__is_leader = False
        self.__leader_exists = False
        self.__answers_count = 0
        self.__take_the_lead_time = 0
        self.__previous_leader = ''

    def __repr__(self) -> str:
        return f'CarTrafficLight({self.id}, {self.state})'

    @property
    def other_monitored_group_queues(self):
        return self.__other_monitored_group_queues

    def monitored_queue_size_add(self, value: int) -> None:
        self.monitored_queue_size += value
        self.monitored_group_queue_size_add(value)
        message = {'id': self.id, 'do': 'change_monitored_queue', 'change': value}
        self.send_message_to_all(message, to_all=False)

    def monitored_group_queue_size_add(self, value: int) -> None:
        self.__monitored_group_queue_size += value
        if self.__is_leader:
            if ((self.__monitored_group_queue_size == 0)
                    or (time.time() - self.__take_the_lead_time > constants.MAX_LEADER_TIME)):
                self.release_the_lead()
        if self.__monitored_group_queue_size < 0:
            self.emergency_shutdown()
            raise RuntimeError(f'Светофор {self.id}: отрицательная очередь')

    def switch_state(self):
        def timer_yellow():
            self.leader_change_state(constants.YELLOW)
            time.sleep(constants.YELLOW_DURATION)
            if self.previous_state == constants.RED:
                self.leader_change_state(constants.GREEN)
            elif self.previous_state == constants.GREEN:
                self.leader_change_state(constants.RED)
        self.yellow_thread = threading.Thread(target=timer_yellow, daemon=True)
        self.yellow_thread.start()

    def leader_change_state(self, state: str) -> None:
        self.change_state(state, leader=self.id)
        # self.__answers_count = 0
        # self.waiting_for_answers()

    def change_state(self, state: str, leader: int | str) -> None:
        is_informative = False
        if self.state != state:
            if state == constants.GREEN:
                self.previous_state = constants.RED
            elif state == constants.RED:
                self.previous_state = constants.GREEN
            elif state == constants.YELLOW:
                self.previous_state = self.state
            self.state = state
            is_informative = True
        message = {'id': self.id, 'leader': leader, 'do': 'change_state', 'state': self.state}
        self.send_message_to_all(message, is_informative=is_informative)

    def waiting_for_answers(self):
        def expectant():
            time.sleep(constants.MAX_RESPONSE_TIME)
            if self.__answers_count == 12:
                self.__answers_count = 0
            else:
                print(f'waiting_for_answers {self.id} {self.__is_leader} ответов {self.__answers_count}')
                self.emergency_shutdown()
        self.expectant_thread = threading.Thread(target=expectant, daemon=True)
        self.expectant_thread.start()

    def take_the_lead(self):
        if not self.__leader_exists:
            self.__is_leader = True
            self.__take_the_lead_time = time.time()
            message = {'id': self.id, 'do': 'leader_taken'}
            self.send_message_to_all(message, to_all=False)
            self.switch_state()

    def release_the_lead(self):
        self.__is_leader = False
        message = {'id': self.id, 'do': 'leader_released'}
        self.send_message_to_all(message, to_all=False)

    def emergency_shutdown(self):
        pass
        # raise RuntimeError('emergency_shutdown')

    def do(self):
        message = self.message_queue_get()
        if 'do' in message:
            id_ = message.get('id')
            do_what = message.get('do')
            if do_what == 'change_state':
                leader_id = message.get('leader')
                if leader_id == id_:
                    leader_state = message.get('state')
                    if leader_state == constants.RED:
                        self.change_state(constants.RED, leader_id)
                    elif leader_state == constants.GREEN:
                        self.change_state(constants.RED, leader_id)
                    elif leader_state == constants.YELLOW:
                        self.change_state(constants.RED, leader_id)
                else:
                    self.__answers_count += 1

            elif do_what == 'change_monitored_queue':
                change = message.get('change')
                if id_ in self.working_group:
                    self.monitored_group_queue_size_add(change)
                else:
                    for key in self.__other_monitored_group_queues.keys():
                        if id_ in key:
                            self.__other_monitored_group_queues[key] += change
            elif do_what == 'leader_released':
                self.__previous_leader = id_
                self.__leader_exists = False
                sorted_other__group_queues = sorted(self.__other_monitored_group_queues.items(),
                                                    key=lambda item: item[1], reverse=True)
                # если групповая очередь больше остальных
                # или больше остальных очередь предыдущего лидера, но собственная групповая очередь вторая по размеру
                if (all(self.__monitored_group_queue_size > queue for queue
                    in self.__other_monitored_group_queues.values())
                        or ((self.__previous_leader in sorted_other__group_queues[0][0])
                            and (self.__monitored_group_queue_size > sorted_other__group_queues[1][1]))):
                    self.take_the_lead()
                    self.__leader_exists = True

            elif do_what == 'leader_taken':
                self.__leader_exists = True

