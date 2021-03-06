import datetime
import pandas
import json
import itertools

import database
import read_json


def get_date_interval(date_from, date_to):
    date_temp = pandas.to_datetime(date_from)
    date_to = pandas.to_datetime(date_to)
    date_interval = list()
    while date_temp <= date_to:
        date_interval.append(date_temp.date())
        date_temp += datetime.timedelta(1)
    return date_interval
def get_daily_table_name(day):
    day = str(day).replace('-', '_')
    return 'daily_' + day
def get_api_response(day):
    json_file_name = get_daily_table_name(day) + '.json'
    with open(json_file_name) as f:
        return json.load(f)
def get_report_table_name(user_ip):
    user_ip = str(user_ip).replace('.', '_')
    table_name = 'report' + '_' + user_ip
    return table_name
def get_history_table_name(key, value):
    table_name = key + '_' + str(value)
    return table_name

def combine_errors(first_error_table, second_error_table, third_error_table):
    first_error = database.get_full_table(first_error_table)
    second_error = database.get_full_table(second_error_table)
    third_error = database.get_full_table(third_error_table)
    resultant_table = list()
    for trans in first_error:
        trans = list(trans)
        trans.append(1)
        resultant_table.append(trans)
    for trans in second_error:
        trans = list(trans)
        trans.append(2)
        resultant_table.append(trans)
    for trans in third_error:
        trans = list(trans)
        trans.append(3)
        resultant_table.append(trans)
    return resultant_table

def make_daily_analysis(date_interval):
    payment_temp_table = 'payment_temp'
    choco_temp_table = 'choco_temp'
    first_error_table = 'first_error'
    second_error_table = 'second_error'
    third_error_table = 'third_error'
    for d in date_interval:
        # transactions from payment systems
        database.create_payment_trans_temp_table(payment_temp_table)
        data = database.get_daily_payment_trans(d)
        database.update_payment_trans_temp_table(payment_temp_table, data)
        # transactions from choco's servers
        transactions = get_api_response(d)
        database.create_choco_temp_table(choco_temp_table)
        date, date_created, order_id, payment_amount, payment_type, payment_reference, status, key_1, key_2 = read_json.read_api_response(
            transactions)
        database.update_choco_temp_table(choco_temp_table, date, date_created, order_id, payment_amount, payment_type,
                                         payment_reference, status, key_1, key_2)
        # магия вне Хогвартса (анализ)
        # temporary tables for errors
        database.create_error_temp_table(first_error_table)
        database.create_error_temp_table(second_error_table)
        database.create_error_temp_table(third_error_table)
        # first error type
        first_error_data = database.get_first_second_errors(payment_temp_table, choco_temp_table)
        database.update_first_error_temp_table(first_error_table, first_error_data)
        # second error type
        second_error_data = database.get_first_second_errors(choco_temp_table, payment_temp_table)
        database.update_second_error_temp_table(second_error_table, second_error_data)
        # third error type
        third_error_payment, third_error_choco, keys = database.get_third_error(first_error_table, second_error_table)
        database.update_third_error_temp_tablle(third_error_table, third_error_payment, third_error_choco)
        # clear first and second error tables from third error type
        database.clear_error_table_by_keys(first_error_table, keys)
        database.clear_error_table_by_keys(second_error_table, keys)
        # combine three tables with errors into one
        errors = combine_errors(first_error_table, second_error_table, third_error_table)
        daily_table_name = get_daily_table_name(d)
        database.create_daily_analysis_table(daily_table_name)
        database.update_daily_tables_table(d)
        database.update_daily_analysis_table(daily_table_name, errors)
        # магия оканчивается
        # clearing database from temporary tables
        database.drop_table(payment_temp_table)
        database.drop_table(choco_temp_table)
        database.drop_table(first_error_table)
        database.drop_table(second_error_table)
        database.drop_table(third_error_table)

def justify_log_len(date_interval):
    max_len = 0
    for d in date_interval:
        log = database.get_log_by_date(d)
        log = log[0][0]
        log = log.split()
        max_len = max(len(log), max_len)
    for d in date_interval:
        log = database.get_log_by_date(d)
        log = log[0][0]
        log = log.split()
        latest_queue = log[-1]
        for i in range(max_len - len(log)):
            log.append(latest_queue)
        log = ' '.join(log)
        database.update_log_table(d, log)

def clear_log(log_list):
    stages = list()
    for i in range(len(log_list[0])):
        temp_stages = list()
        for j in range(len(log_list)):
            temp_stages.append(log_list[j][i])
        stages.append(temp_stages)
    drop_list = list()
    for i in range(len(stages)):
        for j in range(i+1, len(stages)):
            if stages[i] == stages[j]:
                drop_list.append(j)
    drop_list = list(set(drop_list))
    for i in range(len(log_list)):
        for j in drop_list[::-1]:
            del log_list[i][j]
    return log_list

def make_log(date_interval):
    for d in date_interval:
        daily_table_name = get_daily_table_name(d)
        latest_queue = str(database.get_latest_queue(daily_table_name))
        log = database.get_log_by_date(d)
        if len(log) == 0:
            log = str(latest_queue)
        else:
            log = log[0][0]
            log = log.split()
            if log[-1] != latest_queue:
                log.append(latest_queue)
            log = ' '.join(log)
        database.update_log_table(d, log)
    justify_log_len(date_interval)

def make_report(date_from, date_to, report_table_name, payment_systems,latest=True, stage=1):
    date_interval = get_date_interval(date_from, date_to)
    make_daily_analysis(date_interval)
    make_log(date_interval)
    log_list = list()
    for d in date_interval:
        log = database.get_log_by_date(d)
        log = log[0][0].split()
        log_list.append(log)
    log_list = clear_log(log_list)
    if latest:
        stage = 0
    stage_list = list()
    for log in log_list:
        stage_list.append(log[stage-1])
    report_table = list()
    for i in range(len(date_interval)):
        daily_table_name = get_daily_table_name(date_interval[i])
        temp_table = database.get_daily_analysis_table(daily_table_name, payment_systems, latest=False, queue=stage_list[i])
        report_table += temp_table
    database.drop_table(report_table_name)
    database.create_report_table(report_table_name)
    database.update_report_table(report_table_name, report_table)
    return stage, len(log_list[0])

def make_history_table(key, value):
    value = str(value)
    dates = database.get_daily_tables()
    daily_tables = list()
    for date in dates:
        date = date[0]
        table_name = get_daily_table_name(date)
        daily_tables.append(table_name)
    daily_tables.sort()
    full_list = list()
    for table in daily_tables:
        transactions = database.get_trans_by_key_value(table, key, value)
        full_list.append(transactions)
    full_list = list(itertools.chain.from_iterable(full_list))
    # writing to table
    history_table_name = get_history_table_name(key, value)
    database.drop_table(history_table_name)
    database.create_report_table(history_table_name)
    database.update_report_table(history_table_name, full_list)
    return history_table_name




