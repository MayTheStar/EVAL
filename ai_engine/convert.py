import pandas as pd
import json

with open('/Users/rayana/EVAL/rfp_sections.json') as f:
    data = json.load(f)

df = pd.DataFrame(data)
df.to_excel('data.xlsx', index=False)
