from datetime import timedelta

def add_time_strings(time_string1, time_string2):
    total_seconds = 0

    for time_string in [time_string1, time_string2]:
        parts = time_string.split(',')
        hours = float(parts[0].split()[0])
        minutes = float(parts[1].split()[0])
        seconds = float(parts[2].split()[0])

        total_seconds += timedelta(hours=hours, minutes=minutes, seconds=seconds).total_seconds()

    total_timedelta = timedelta(seconds=total_seconds)
    hours, remainder = divmod(total_timedelta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return f"{hours:.1f} giờ, {minutes:.1f} phút, {seconds:.2f} giây"

time_string1 = "1.0 giờ, 59.0 phút, 0 giây"
time_string2 = "2.0 giờ, 0.0 phút, 0 giây"
result = add_time_strings(time_string1, time_string2)
print(result)
