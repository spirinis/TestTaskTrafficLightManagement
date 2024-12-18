import time
from sources import traffic_lights
from sources.communication import Communication
import sources.constants as constants

if __name__ == '__main__':
    list_car_traffic_lights = []
    list_pedestrian_traffic_lights = []
    car_traffic_light_ids = ('с Запада', 'с Севера', 'с Востока', 'с Юга',)
    # вложенность для распределения по рабочим группам
    pedestrian_traffic_light_ids = (('с Севера на Запад', 'с Севера на Восток'),
                                    ('с Востока на Север', 'с Востока на Юг'),
                                    ('с Юга на Запад', 'с Юга на Восток'),
                                    ('с Запада на Север', 'с Запада на Юг'),)
    # создание объектов 4 автомобильных светофоров
    # север сверху
    for ids_i in range(len(car_traffic_light_ids)):
        id_ = car_traffic_light_ids[ids_i]
        # указание объектам светофоров адресов своих рабочих групп
        # рабочая группа изменяет состояние одновременно, имеет общую очередь
        working_group = tuple(pedestrian_traffic_light_ids[ids_i])

        traffic_light = traffic_lights.CarTrafficLight(id_, working_group)

        # передача "адресов" для моделирования связи нескольких устройств
        Communication.ALL_TRAFFIC_LIGHTS.update({id_: traffic_light})
        list_car_traffic_lights.append(traffic_light)

    # создание объектов 8 пешеходных светофоров
    for group_ids_i in range(len(pedestrian_traffic_light_ids)):
        for ids_i in range(len(pedestrian_traffic_light_ids[group_ids_i])):
            id_ = pedestrian_traffic_light_ids[group_ids_i][ids_i]
            # указание объектам светофоров адресов своих рабочих групп
            working_group = (car_traffic_light_ids[group_ids_i],
                             *set(pedestrian_traffic_light_ids[group_ids_i]) - {id_})

            traffic_light = traffic_lights.PedestrianTrafficLight(id_, working_group)

            # передача "адресов" для моделирования связи нескольких устройств
            Communication.ALL_TRAFFIC_LIGHTS.update({id_: traffic_light})
            list_pedestrian_traffic_lights.append(traffic_light)
    del group_ids_i, ids_i, id_, working_group, traffic_light

    # указание объектам светофоров адресов других рабочих групп
    for car_traffic_light in list_car_traffic_lights:
        for i_id in range(len(car_traffic_light_ids)):
            if car_traffic_light_ids[i_id] != car_traffic_light.id:
                group_ids = ()
                group_ids += (car_traffic_light_ids[i_id], *pedestrian_traffic_light_ids[i_id])
                car_traffic_light.other_monitored_group_queues.update({group_ids: 0})
    del car_traffic_light, i_id, group_ids, car_traffic_light_ids, pedestrian_traffic_light_ids

    ctl_w, ctl_n, ctl_e, ctl_s, = list_car_traffic_lights
    ptl_nw, ptl_ne, ptl_en, ptl_es, *args = list_pedestrian_traffic_lights

    def simulation_of_queue_movement(traffic_light_: traffic_lights.TrafficLight) -> bool:
        """Симулирует движение очередей по одному на зелёный сигнал. Возвращает True, если очередь пуста"""
        if traffic_light_.monitored_queue_size > 0:
            if traffic_light_.state == constants.GREEN:
                traffic_light_.monitored_queue_size_add(-1)
                return False
        else:
            return True

    # ситуация с тремя разными очередями с участием пешеходов
    # ctl_w.monitored_queue_size_add(3)
    # ctl_e.monitored_queue_size_add(6)
    #
    # ctl_n.monitored_queue_size_add(2)
    # ptl_en.monitored_queue_size_add(1)
    # ptl_es.monitored_queue_size_add(2)

    # ситуация с "бесконечным" потоком
    ctl_w.monitored_queue_size_add(15)
    ctl_e.monitored_queue_size_add(4)

    # отправка пакета об окончании работы лидера, за которым последует установление нового лидера и запуск системы
    print(f"{'НАЧАЛО СИМУЛЯЦИИ':=^100}")
    ctl_n.release_the_lead()

    list_all_traffic_lights = list_car_traffic_lights + list_pedestrian_traffic_lights
    while True:
        queues_emptiness = []
        for traffic_light in list_all_traffic_lights:
            queues_emptiness.append(simulation_of_queue_movement(traffic_light))
        time.sleep(constants.CROSSING_TIME)
        # остановка симуляции, если все очереди пусты
        if bool(queues_emptiness) and all(queues_emptiness):
            break
    print(f"{'КОНЕЦ СИМУЛЯЦИИ':=^100}")
