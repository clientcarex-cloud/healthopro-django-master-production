import datetime
import threading

import schedule
import time
from pro_laboratory.views.subscription_data_views import check_completed_business_plans


def check_scheduling_running_status():
    print('Scheduling is working fine', datetime.datetime.now().strftime('%d-%m-%y %I:%M:%S %p'))


def run_scheduler():
    print('Scheduled tasks are running')
    schedule.every(10).minutes.do(check_scheduling_running_status)
    schedule.every().day.at("06:00").do(check_completed_business_plans)
    while True:
        schedule.run_pending()
        time.sleep(1)


scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.daemon = True
scheduler_thread.start()