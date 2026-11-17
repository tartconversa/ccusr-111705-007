"""只审阅已观察的详情入口，不把候选记录当作已完成的业务。"""

def review_entries(entries):
    accessibility = []
    for entry in entries:
        detail = entry['detail_fact']
        accessibility.append({'service_floor': detail['business_key'], 'service_day': detail['service_day'],
                              'keyboard_path': 'not_observed', 'booking': 'unconfirmed'})
    return accessibility
