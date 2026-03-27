import csv
import os
from datetime import datetime


class DataManager:
    def __init__(self, config_folder="Config"):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_folder = os.path.join(base_dir, config_folder)

    def _read_csv(self, filename):
        filepath = os.path.join(self.config_folder, filename)
        if not os.path.exists(filepath):
            return []
        with open(filepath, mode='r', encoding='utf-8-sig', errors='replace') as file:
            return list(csv.DictReader(file))

    def get_users_full(self):
        return self._read_csv("USERACCOUNT.csv")

    def get_users(self):
        data = self._read_csv("USERACCOUNT.csv")
        return [row['User_Name'] for row in data if row.get('User_Name') and row.get('Active', 'Yes').lower() == 'yes']

    def validate_login(self, username, password):
        data = self._read_csv("USERACCOUNT.csv")
        for user in data:
            if user.get('User_Name') == username and user.get('Password') == str(password):
                if user.get('Active', 'Yes').lower() == 'yes':
                    return True, user
        return False, None

    def get_system_setup(self):
        data = self._read_csv("SYSTEM_SETUP.csv")
        return data[0] if data else {}

    def get_dashboard_stats(self):
        parts_data = self._read_csv("Cable_Tuning_setup.csv")
        total_parts = len([r for r in parts_data if r.get('PART_NUMBER')])
        total_tests = 0
        filepath = os.path.join(self.config_folder, "Report.csv")
        if os.path.exists(filepath):
            with open(filepath, "r", encoding='utf-8-sig', errors='replace') as f:
                total_tests = max(0, sum(1 for line in f) - 1)
        return total_parts, total_tests

    def get_part_numbers(self):
        data = self._read_csv("Cable_Tuning_setup.csv")
        return [row['PART_NUMBER'] for row in data if 'PART_NUMBER' in row and row['PART_NUMBER'].strip() != ""]

    def get_part_details(self, part_number):
        data = self._read_csv("Cable_Tuning_setup.csv")
        for row in data:
            if row.get('PART_NUMBER') == part_number:
                return row
        return None

    def get_na_setup(self, setup_id):
        """Fetches dynamic VNA configuration based on SETUP_ID."""
        data = self._read_csv("NA_SETUP.csv")
        cleaned_data = [{k.strip(): v for k, v in row.items()} for row in data]
        for row in cleaned_data:
            if row.get('SETUP_ID') == setup_id:
                return row
        return None

    def get_capacitors(self):
        data = self._read_csv("Capacitor.csv")
        fixed = [row['Fixed'] for row in data if row.get('Fixed', '').strip()]
        tuned = [row['Tuned'] for row in data if row.get('Tuned', '').strip()]
        return fixed, tuned

    def get_all_reports(self):
        return self._read_csv("Report.csv")

    def get_equipment(self):
        return self._read_csv("EquipmentList.csv")

    def save_users(self, data_list):
        filepath = os.path.join(self.config_folder, "USERACCOUNT.csv")
        with open(filepath, mode='w', newline='', encoding='utf-8-sig') as file:
            writer = csv.DictWriter(file, fieldnames=["User_Name", "Password", "Role", "Active"])
            writer.writeheader()
            writer.writerows(data_list)

    def save_equipment(self, data_list):
        filepath = os.path.join(self.config_folder, "EquipmentList.csv")
        with open(filepath, mode='w', newline='', encoding='utf-8-sig') as file:
            writer = csv.DictWriter(file, fieldnames=["Equipment_Name", "Asset_ID", "Cal_Due_Date", "Status"])
            writer.writeheader()
            writer.writerows(data_list)

    def find_incomplete_report(self, pn, sn, wo):
        reports = self._read_csv("Report.csv")
        for report in reversed(reports):
            if report.get('PN') == pn and report.get('SL') == sn and report.get('WO') == wo:
                if report.get('Result') not in ['PASS', 'FAIL']:
                    return report
        return None

    def save_or_update_report(self, record_dict):
        filepath = os.path.join(self.config_folder, "Report.csv")
        reports = self._read_csv("Report.csv")

        headers = [
            "ID", "Tuning_Date", "Tuning_Time", "PN", "SL", "WO", "Descrip", "User", "Result", "Spend_Hours",
            "Stage1", "Freq1Low", "Freq1High", "Freq1Data", "Freq1Result", "Attn1Low", "Attn1High", "Attn1Data",
            "Attn1Result",
            "Stage2", "Freq2Low", "Freq2High", "Freq2Data", "Freq2Result", "Attn2Low", "Attn2High", "Attn2Data",
            "Attn2Result",
            "Stage3", "Freq3Low", "Freq3High", "Freq3Data", "Freq3Result", "Attn3Low", "Attn3High", "Attn3Data",
            "Attn3Result",
            "Stage4", "Freq4Low", "Freq4High", "Freq4Data", "Freq4Result", "Attn4Low", "Attn4High", "Attn4Data",
            "Attn4Result",
            "SW_REV", "Test_Station", "NA", "NA_CalDate", "PS", "PS_CalDate", "DMM", "DMM_CalDate", "Reserved1",
            "Reserved2"
        ]

        existing_idx = None
        if record_dict.get('ID'):
            for i, r in enumerate(reports):
                if r.get('ID') == record_dict.get('ID'):
                    existing_idx = i
                    break

        if existing_idx is not None:
            for k, v in record_dict.items():
                reports[existing_idx][k] = v
        else:
            new_id = "0000001"
            if reports and 'ID' in reports[-1] and reports[-1]['ID'].isdigit():
                new_id = f"{int(reports[-1]['ID']) + 1:07d}"
            record_dict['ID'] = new_id

            for h in headers:
                if h not in record_dict: record_dict[h] = ""
            reports.append(record_dict)

        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(reports)

        return record_dict['ID']