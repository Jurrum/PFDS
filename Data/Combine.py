import os
import pandas as pd

# Adjust to your base directory path
root_dir = 'Data'
output_file = 'merged_questionnaires.xlsx'

pre_data, post_data, log_data = [], [], []

for subdir, _, files in os.walk(root_dir):
    for file in files:
        full_path = os.path.join(subdir, file)
        
        if file.endswith('_pre_questionnaire.csv'):
            df = pd.read_csv(full_path)
            df['source'] = os.path.basename(subdir)  # Optional: tag source folder
            pre_data.append(df)
        
        elif file.endswith('_post_questionnaire.csv'):
            df = pd.read_csv(full_path)
            df['source'] = os.path.basename(subdir)
            post_data.append(df)
        
        elif file == 'session_log.csv':
            df = pd.read_csv(full_path)
            df['source'] = os.path.basename(subdir)
            log_data.append(df)

# Combine and write to Excel
with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    if pre_data:
        pd.concat(pre_data, ignore_index=True).to_excel(writer, sheet_name='PRE Questionnaire', index=False)
    if post_data:
        pd.concat(post_data, ignore_index=True).to_excel(writer, sheet_name='POST Questionnaire', index=False)
    if log_data:
        pd.concat(log_data, ignore_index=True).to_excel(writer, sheet_name='Session Logs', index=False)

print(f"✅ All files merged into {output_file}")
