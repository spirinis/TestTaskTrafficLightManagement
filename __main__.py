import time
import threading
from sources import traffic_lights
from sources.communication import Communication
import sources.constants as constants

if __name__ == '__main__':
    list_car_traffic_lights = []
    list_pedestrian_traffic_lights = []
    # создание объектов 4 автомобильных светофоров
    # север сверху
    for ids_i in range(len(constants.CAR_TRAFFIC_LIGHT_IDS)):
        id_ = constants.CAR_TRAFFIC_LIGHT_IDS[ids_i]
        # указание объектам светофоров адресов своих рабочих групп
        # рабочая группа изменяет состояние одновременно, имеет общую очередь
        working_group = tuple(constants.PEDESTRIAN_TRAFFIC_LIGHT_IDS[ids_i])

        traffic_light = traffic_lights.CarTrafficLight(id_, working_group)

        # передача "адресов" для моделирования связи нескольких устройств
        Communication.ALL_TRAFFIC_LIGHTS.update({id_: traffic_light})
        list_car_traffic_lights.append(traffic_light)

    # создание объектов 8 пешеходных светофоров
    for group_ids_i in range(len(constants.PEDESTRIAN_TRAFFIC_LIGHT_IDS)):
        for ids_i in range(len(constants.PEDESTRIAN_TRAFFIC_LIGHT_IDS[group_ids_i])):
            id_ = constants.PEDESTRIAN_TRAFFIC_LIGHT_IDS[group_ids_i][ids_i]
            # указание объектам светофоров адресов своих рабочих групп
            working_group = (constants.CAR_TRAFFIC_LIGHT_IDS[group_ids_i],
                             *set(constants.PEDESTRIAN_TRAFFIC_LIGHT_IDS[group_ids_i]) - {id_})

            traffic_light = traffic_lights.PedestrianTrafficLight(id_, working_group)

            # передача "адресов" для моделирования связи нескольких устройств
            Communication.ALL_TRAFFIC_LIGHTS.update({id_: traffic_light})
            list_pedestrian_traffic_lights.append(traffic_light)
    del group_ids_i, ids_i, id_, working_group, traffic_light

    # указание объектам светофоров адресов других рабочих групп
    for car_traffic_light in list_car_traffic_lights:
        for i_id in range(len(constants.CAR_TRAFFIC_LIGHT_IDS)):
            if constants.CAR_TRAFFIC_LIGHT_IDS[i_id] != car_traffic_light.id:
                group_ids = ()
                group_ids += (constants.CAR_TRAFFIC_LIGHT_IDS[i_id], *constants.PEDESTRIAN_TRAFFIC_LIGHT_IDS[i_id])
                car_traffic_light.other_monitored_group_queues.update({group_ids: 0})
    del car_traffic_light, i_id, group_ids, constants.CAR_TRAFFIC_LIGHT_IDS, constants.PEDESTRIAN_TRAFFIC_LIGHT_IDS

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

    def destroy_the_traffic_light(wait):
        """Сломает восточный автомобильный светофор через wait секунд"""
        def destroyer():
            time.sleep(wait)
            global ctl_e
            # Это что? Бэкдор? Если переопределить id для нарушения связи или присвоить класс предок у меня
            # защиты от дурака ругаются
            ctl_e.not_broken = False
        destroyer_thread = threading.Thread(target=destroyer, daemon=True)
        destroyer_thread.start()

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

    # сломать светофор "с Востока"
    destroy_the_traffic_light(wait=10)

    # отправка пакета об окончании работы лидера, за которым последует установление нового лидера и запуск системы
    print(f"{'НАЧАЛО СИМУЛЯЦИИ':=^100}")
    ctl_n.release_the_lead()

    list_all_traffic_lights = list_car_traffic_lights + list_pedestrian_traffic_lights
    while True:
        queues_emptiness = []
        for traffic_light in list_all_traffic_lights:
            queues_emptiness.append(simulation_of_queue_movement(traffic_light))
        time.sleep(constants.CROSSING_TIME)
        # остановка симуляции, если все очереди пусты, или если светофоры перешли в аварийный режим
        if ((bool(queues_emptiness) and all(queues_emptiness))
                or any((traffic_light.emergency for traffic_light in list_car_traffic_lights))):
            break
    print(f"{'КОНЕЦ СИМУЛЯЦИИ':=^100}")
