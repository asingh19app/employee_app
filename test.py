import uuid
from datetime import datetime, timedelta

def gen_id():
    id = f"E{uuid.uuid4().hex[:8]}"
    print(id)

gen_id()


# duration = timedelta(days=1,hours=5,minutes = 30)
# print(duration)

in_time = datetime(2024,11,29,9,10)
out_time = datetime(2024,11,29,17,35)

duration = out_time - in_time
print(duration)

total_secs = duration.total_seconds()
print(total_secs)
