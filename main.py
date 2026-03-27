import sys
import csv
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMessageBox, QTableWidgetItem, QComboBox, QFileDialog, QCheckBox
from PyQt6.QtCore import Qt, QTimer, QDateTime, QTime, QDate, QEventLoop
from PyQt6.QtGui import QColor

from main_gui import IndustrialUI
from data_manager import DataManager

# ==========================================
# HARDWARE CONFIGURATION
# ==========================================
DEBUG_MODE = False  # Set to False to connect to physical VNA via PyVISA
VNA_ADDRESS = "GPIB0::17::INSTR"


class VNAManager:
    def __init__(self):
        self.rm = None
        self.vna = None
        self.is_connected = False

    def connect(self):
        if DEBUG_MODE or self.is_connected:
            return True
        try:
            import pyvisa
            self.rm = pyvisa.ResourceManager()
            self.vna = self.rm.open_resource(VNA_ADDRESS)
            self.vna.timeout = 5000
            self.vna.write("*CLS")
            self.is_connected = True
            print(f"VNA Connected Successfully at {VNA_ADDRESS}")
            return True
        except Exception as e:
            print(f"VNA Connection failed: {e}")
            self.is_connected = False
            return False

    def write(self, cmd):
        if DEBUG_MODE or not self.is_connected: return
        try:
            self.vna.write(cmd)
        except Exception as e:
            print(f"SCPI Write Error: {e}")

    def query(self, cmd):
        if DEBUG_MODE or not self.is_connected:
            if "STAT?" in cmd: return "1"
            if "*OPC?" in cmd: return "1"
            if "FDAT?" in cmd: return "-0.5,-25.0,0.0"
            if "MARK2:X?" in cmd: return "63860000.0"
            if "MARK2:Y?" in cmd: return "-26.5,0.0"
            return "1"
        try:
            return self.vna.query(cmd).strip()
        except Exception as e:
            print(f"SCPI Query Error: {e}")
            return ""


class MainController:
    def __init__(self):
        self.ui = IndustrialUI()
        self.db = DataManager()
        self.vna = VNAManager()

        self.current_user = None
        self.session_time = QTime(0, 0, 0)
        self.session_timer = QTimer()
        self.session_timer.timeout.connect(self.update_session_timer)

        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)

        self.tuning_seconds = 0
        self.tuning_timer = QTimer()
        self.tuning_timer.timeout.connect(self.increment_tuning_time)
        self.current_report_id = None

        self.live_update_timer = QTimer()
        self.live_update_timer.timeout.connect(self.fetch_live_vna_data)

        self.is_calibrating = False
        self.cal_step = 0
        self.cal_popup = None
        self.cal_sequence = [0, 2, 4, 1, 3, 5, 6]
        self.cal_cmds = {
            0: ":SENS1:CORR:COLL:OPEN 1", 1: ":SENS1:CORR:COLL:OPEN 2",
            2: ":SENS1:CORR:COLL:SHOR 1", 3: ":SENS1:CORR:COLL:SHOR 2",
            4: ":SENS1:CORR:COLL:LOAD 1", 5: ":SENS1:CORR:COLL:LOAD 2",
            6: ":SENS1:CORR:COLL:ACQ:THRU 1,2\n:SENS1:CORR:COLL:ACQ:THRU 2,1"
        }
        self.cal_names = {
            0: "OPEN to Port 1", 1: "OPEN to Port 2", 2: "SHORT to Port 1",
            3: "SHORT to Port 2", 4: "LOAD to Port 1", 5: "LOAD to Port 2", 6: "THRU (Port 1 to Port 2)"
        }

        self.val_step = 0
        self.val_passed_overall = True
        self.val_sequence = [
            {"name": "OPEN to both ports", "param": "S11"},
            {"name": "SHORT to both ports", "param": "S11"},
            {"name": "LOAD to both ports", "param": "S11"},
            {"name": "THRU (Port1 ↔ Port2)", "param": "S21"}
        ]

        self.cal_pressed_indices = set()
        self._is_updating = False

        self.populate_initial_data()
        self.connect_signals()

        self.update_status("Enter User name and password", "white")
        self.ui.show()

    def update_clock(self):
        self.ui.datetime_label.setText(QDateTime.currentDateTime().toString("yyyy-MM-dd | hh:mm:ss AP"))

    def update_session_timer(self):
        self.session_time = self.session_time.addSecs(1)
        if self.current_user:
            self.ui.user_info_label.setText(
                f"User: {self.current_user['User_Name']} | Role: {self.current_user.get('Role', 'Operator')} | Session: {self.session_time.toString('hh:mm:ss')}")

    def increment_tuning_time(self):
        self.tuning_seconds += 1
        h, rem = divmod(self.tuning_seconds, 3600)
        m, s = divmod(rem, 60)
        self.ui.test_time_lbl.setText(f" Time: {h:02d}:{m:02d}:{s:02d} ")

    def populate_initial_data(self):
        users = self.db.get_users()
        if users:
            self.ui.user_combo.addItems(users)
            self.ui.flt_user.addItems(users)

        sys_setup = self.db.get_system_setup()
        self.ui.lbl_version.setText(f"<b>Application Version:</b> {sys_setup.get('SOFTWARE_REV', '1.0.0')}")

        parts = self.db.get_part_numbers()
        if parts:
            self.ui.pn_combo.addItems(parts)
            self.ui.pn_combo.setCurrentIndex(-1)
            self.ui.flt_pn.addItems(parts)

        self.populate_dashboard_and_tables()

    def populate_dashboard_and_tables(self):
        total_pn, total_tests = self.db.get_dashboard_stats()
        self.ui.total_pn_lbl.setText(f"{total_pn:,}")
        self.ui.total_tests_lbl.setText(f"{total_tests:,}")

        eq_data = self.db.get_equipment()
        self.ui.eq_table.setRowCount(len(eq_data))
        self.ui.maint_table.setRowCount(len(eq_data))
        current_date = QDate.currentDate()

        for r, row in enumerate(eq_data):
            due_date_str = row.get('Cal_Due_Date', '')
            status, color = "UNKNOWN", QColor("#aaaaaa")
            due_date = QDate.fromString(due_date_str, "yyyy-MM-dd")
            if due_date.isValid():
                if due_date < current_date:
                    status, color = "CALIBRATION OUT", QColor("#f44336")
                else:
                    status, color = "READY!", QColor("#4caf50")

            items = [row.get('Equipment_Name', ''), row.get('Asset_ID', ''), due_date_str, status]
            for c, item in enumerate(items):
                cell1, cell2 = QTableWidgetItem(item), QTableWidgetItem(item)
                cell1.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                cell2.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if c == 3: cell1.setForeground(color); cell1.setFont(self.ui.font())
                self.ui.eq_table.setItem(r, c, cell1)
                self.ui.maint_table.setItem(r, c, cell2)

        users_full = self.db.get_users_full()
        self.ui.users_table.setRowCount(len(users_full))
        for r, row in enumerate(users_full):
            self.add_user_row_ui(r, row.get('User_Name', ''), row.get('Password', ''), row.get('Role', 'Operator'),
                                 row.get('Active', 'Yes'))

    def populate_reports_table(self):
        reports = self.db.get_all_reports()
        self.ui.reports_table.setSortingEnabled(False)
        self.ui.reports_table.setRowCount(len(reports))
        for r, row in enumerate(reversed(reports)):
            for c, header in enumerate(self.ui.report_headers):
                self.ui.reports_table.setItem(r, c, QTableWidgetItem(row.get(header, '')))
        self.ui.reports_table.setSortingEnabled(True)

    def apply_reports_filter(self, *args):
        d_start = self.ui.flt_date_start.date().toPyDate()
        d_end = self.ui.flt_date_end.date().toPyDate()
        f_user = self.ui.flt_user.currentText()
        f_pn = self.ui.flt_pn.currentText()
        f_wo = self.ui.flt_wo.text().strip().lower()
        f_stat = self.ui.flt_status.currentText()

        date_formats = ["%Y/%m/%d", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y"]

        for r in range(self.ui.reports_table.rowCount()):
            show = True
            date_str = self.ui.reports_table.item(r, 1).text().strip() if self.ui.reports_table.item(r, 1) else ""
            row_date = None
            if date_str:
                for fmt in date_formats:
                    try:
                        row_date = datetime.strptime(date_str, fmt).date()
                        break
                    except ValueError:
                        pass

            if row_date and not (d_start <= row_date <= d_end): show = False
            if f_user != "All Users" and self.ui.reports_table.item(r, 7).text() != f_user: show = False
            if f_pn != "All Parts" and self.ui.reports_table.item(r, 3).text() != f_pn: show = False
            if f_wo and f_wo not in self.ui.reports_table.item(r, 5).text().lower(): show = False
            if f_stat != "All" and self.ui.reports_table.item(r, 8).text() != f_stat: show = False

            self.ui.reports_table.setRowHidden(r, not show)

    def clear_reports_filter(self, *args):
        self.ui.flt_date_start.setDate(QDate.currentDate().addDays(-30))
        self.ui.flt_date_end.setDate(QDate.currentDate())
        self.ui.flt_user.setCurrentIndex(0)
        self.ui.flt_pn.setCurrentIndex(0)
        self.ui.flt_wo.clear()
        self.ui.flt_status.setCurrentIndex(0)
        for r in range(self.ui.reports_table.rowCount()):
            self.ui.reports_table.setRowHidden(r, False)

    def export_reports_csv(self, *args):
        path, _ = QFileDialog.getSaveFileName(self.ui, "Export Reports", "", "CSV Files (*.csv)")
        if not path: return
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(self.ui.report_headers)
            for r in range(self.ui.reports_table.rowCount()):
                if not self.ui.reports_table.isRowHidden(r):
                    writer.writerow(
                        [self.ui.reports_table.item(r, c).text() if self.ui.reports_table.item(r, c) else "" for c in
                         range(len(self.ui.report_headers))])
        self.update_status("Reports Exported.", "white", "#4caf50")

    def add_user_row_ui(self, r, username="", pwd="", role="Operator", active="Yes"):
        self.ui.users_table.setItem(r, 0, QTableWidgetItem(username))
        pwd_item = QTableWidgetItem("***" if pwd else "")
        pwd_item.setData(Qt.ItemDataRole.UserRole, pwd)
        self.ui.users_table.setItem(r, 1, pwd_item)
        role_cb = QComboBox()
        role_cb.addItems(["Admin", "Engineer", "Operator", "QA"])
        role_cb.setCurrentText(role)
        self.ui.users_table.setCellWidget(r, 2, role_cb)
        active_cb = QComboBox()
        active_cb.addItems(["Yes", "No"])
        active_cb.setCurrentText(active)
        self.ui.users_table.setCellWidget(r, 3, active_cb)

    def connect_signals(self):
        self.ui.login_btn.clicked.connect(self.handle_login)
        self.ui.logout_btn.clicked.connect(self.handle_logout)

        def make_nav_slot(key):
            idx = ["home", "tune", "cal", "reports", "maint", "about"].index(key) + 1
            return lambda checked=False: self.navigate_to(idx, key)

        for k, btn in self.ui.nav_buttons.items():
            btn.clicked.connect(make_nav_slot(k))

        self.ui.home_btn.clicked.connect(lambda checked=False: self.navigate_to(1, 'home'))
        self.ui.btn_start_tune.clicked.connect(lambda checked=False: self.navigate_to(2, 'tune'))

        self.ui.btn_start_cal.clicked.connect(self.handle_start_cal)
        self.ui.btn_clear_log.clicked.connect(self.clear_calibration_log)

        def make_cal_slot(index):
            return lambda checked=False: self.process_cal_step(index, is_manual=True)

        for idx, btn in enumerate(self.ui.cal_btns):
            btn.clicked.connect(make_cal_slot(idx))

        self.ui.pn_combo.currentTextChanged.connect(self.update_unit_title)
        self.ui.pn_combo.currentTextChanged.connect(self.check_tune_top_ok)
        self.ui.sn_input.textChanged.connect(self.check_tune_top_ok)
        self.ui.wo_combo.currentTextChanged.connect(self.check_tune_top_ok)
        self.ui.ok_top_btn.clicked.connect(self.handle_tune_top_ok)
        self.ui.clear_btn.clicked.connect(lambda checked=False: self.clear_tune_data(full=True))

        self.ui.btn_tune_cal.clicked.connect(lambda checked=False: self.navigate_to(3, 'cal', preserve_tune=True))

        for stage in self.ui.stage_ui_elements:
            self.bind_stage_signals(stage)

        self.ui.btn_add_user.clicked.connect(
            lambda checked=False: [self.ui.users_table.insertRow(self.ui.users_table.rowCount()),
                                   self.add_user_row_ui(self.ui.users_table.rowCount() - 1)])
        self.ui.btn_del_user.clicked.connect(self.delete_selected_user)
        self.ui.btn_save_user.clicked.connect(self.handle_save_users)
        self.ui.btn_add_eq.clicked.connect(
            lambda checked=False: self.ui.maint_table.insertRow(self.ui.maint_table.rowCount()))
        self.ui.btn_del_eq.clicked.connect(self.delete_selected_eq)
        self.ui.btn_save_eq.clicked.connect(self.handle_save_equipment)

        self.ui.btn_apply_filter.clicked.connect(self.apply_reports_filter)
        self.ui.btn_clear_filter.clicked.connect(self.clear_reports_filter)
        self.ui.btn_export_csv.clicked.connect(self.export_reports_csv)

        self.bind_right_menu_signals()

    def bind_right_menu_signals(self):
        format_map = {"Log Mag": "MLOG", "Lin Mag": "MLIN", "Phase": "PHAS", "SWR": "SWR", "Smith": "SMIT"}

        self.ui.plot_cb.currentTextChanged.connect(
            lambda t: [self.vna.connect(), self.vna.write(f":CALC1:FORM {format_map.get(t, 'MLOG')}")])
        self.ui.smat_cb.currentTextChanged.connect(
            lambda t: [self.vna.connect(), self.vna.write(f":CALC1:PAR1:DEF {t}")])
        self.ui.btn_auto_scale.clicked.connect(
            lambda c=False: [self.vna.connect(), self.vna.write(":DISP:WIND1:TRAC1:Y:AUTO")])
        self.ui.btn_right_apply.clicked.connect(lambda c=False: self.apply_right_settings())

        def toggle_avg(*args):
            self.vna.connect()
            state = "ON" if self.ui.avg_btn.isChecked() else "OFF"
            self.vna.write(f":SENS1:AVER {state}")

        self.ui.avg_btn.clicked.connect(toggle_avg)

        def toggle_rf(*args):
            self.vna.connect()
            state = "ON" if self.ui.rf_btn.isChecked() else "OFF"
            self.vna.write(f":OUTP {state}")

        self.ui.rf_btn.clicked.connect(toggle_rf)

        def m1_track_changed(t):
            self.vna.connect()
            self.vna.write(":CALC1:MARK1 ON")
            if t == "OFF":
                self.vna.write(":CALC1:MARK1:FUNC:TRAC OFF")
            elif t == "MAX (Peak)":
                self.vna.write(":CALC1:MARK1:FUNC:TYPE MAX")
                self.vna.write(":CALC1:MARK1:FUNC:TRAC ON")
            elif t == "MIN (Dip)":
                self.vna.write(":CALC1:MARK1:FUNC:TYPE MIN")
                self.vna.write(":CALC1:MARK1:FUNC:TRAC ON")

        self.ui.m1_track_cb.currentTextChanged.connect(m1_track_changed)

        def apply_m2(*args):
            self.vna.connect()
            if self.ui.m2_chk.isChecked():
                self.vna.write(":CALC1:MARK2 ON")
                try:
                    self.vna.write(f":CALC1:MARK2:X {float(self.ui.m2_freq_in.text()) * 1e6}")
                except:
                    pass
            else:
                self.vna.write(":CALC1:MARK2 OFF")

        self.ui.m2_chk.clicked.connect(apply_m2)
        self.ui.m2_freq_in.returnPressed.connect(apply_m2)

        def apply_m3(*args):
            self.vna.connect()
            if self.ui.m3_chk.isChecked():
                self.vna.write(":CALC1:MARK3 ON")
                try:
                    self.vna.write(f":CALC1:MARK3:X {float(self.ui.m3_freq_in.text()) * 1e6}")
                except:
                    pass
            else:
                self.vna.write(":CALC1:MARK3 OFF")

        self.ui.m3_chk.clicked.connect(apply_m3)
        self.ui.m3_freq_in.returnPressed.connect(apply_m3)

        def clear_mkrs(*args):
            self.vna.connect()
            self.vna.write(":CALC1:MARK1 OFF")
            self.vna.write(":CALC1:MARK2 OFF")
            self.vna.write(":CALC1:MARK3 OFF")
            self.ui.m1_track_cb.setCurrentText("OFF")
            self.ui.m2_chk.setChecked(False)
            self.ui.m3_chk.setChecked(False)

        self.ui.btn_clear_markers.clicked.connect(lambda c=False: clear_mkrs())

    def apply_right_settings(self, *args):
        self.vna.connect()
        try:
            self.vna.write(f":SENS1:FREQ:CENT {float(self.ui.r_freq_in.text()) * 1e6}")
        except:
            pass
        try:
            self.vna.write(f":SENS1:FREQ:SPAN {float(self.ui.r_span_in.text()) * 1e6}")
        except:
            pass
        try:
            self.vna.write(f":SOUR1:POW {float(self.ui.r_pow_in.text())}")
        except:
            pass
        self.vna.write(f":SENS1:SWE:POIN {self.ui.points_cb.currentText()}")
        self.update_status("VNA Settings Applied", "white", "#4caf50")

    def bind_stage_signals(self, stage_dict):
        stage_dict['btn_retest'].clicked.connect(self.handle_retest)
        stage_dict['btn_confirm'].clicked.connect(lambda checked=False, s=stage_dict: self.handle_tune_confirm(s))

        def toggle_leason(*args):
            state = stage_dict['btn_leason'].isChecked()
            stage_dict['btn_leason'].setText("START/STOP: ON" if state else "START/STOP: OFF")
            if state:
                self.live_update_timer.start(800)
            else:
                self.live_update_timer.stop()

        stage_dict['btn_leason'].clicked.connect(toggle_leason)

        stage_dict['m_input'].textChanged.connect(lambda t, s=stage_dict: self.safe_validate(s))
        stage_dict['attn_m_input'].textChanged.connect(lambda t, s=stage_dict: self.safe_validate(s))

        stage_dict['m_input'].textChanged.connect(lambda t, s=stage_dict: self.update_freq_graph(t, s))
        stage_dict['attn_m_input'].textChanged.connect(lambda t, s=stage_dict: self.update_attn_graph(t, s))

    def safe_validate(self, stage):
        if self._is_updating: return
        if stage['m_input'].text().strip():
            # Checking isVisible() because frame is completely hidden if not needed
            if stage['attn_frame'].isVisible() and not stage['attn_m_input'].text().strip():
                stage['btn_confirm'].setEnabled(False)
            else:
                stage['btn_confirm'].setEnabled(True)
        else:
            stage['btn_confirm'].setEnabled(False)

    def update_status(self, text, color="white", bg_color="transparent"):
        self.ui.status_label.setText(text)
        self.ui.status_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {color}; background-color: {bg_color}; padding: 4px; border-radius: 4px;")

    def navigate_to(self, index, btn_key, preserve_tune=False):
        self.ui.stacked_widget.setCurrentIndex(index)
        for key, btn in self.ui.nav_buttons.items():
            btn.setStyleSheet(self.ui.active_btn_style if key == btn_key else self.ui.inactive_btn_style)

        if index == 1:
            self.populate_dashboard_and_tables()
            self.update_status("Logged in Sucessfuly, Start VNA Calibration", "white")
        elif index == 2:
            if not preserve_tune:
                self.clear_tune_data(full=True)
                self.update_status("Enter Unit Details", "white")
            else:
                self.update_status("Testing in progress...", "white", "#f57c00")
        elif index == 3:
            if len(self.cal_pressed_indices) < 7:
                self.update_status("Start Calibration", "white")
            else:
                self.update_status("Verify Calibration", "white")
        elif index == 4:
            self.populate_reports_table()
            self.clear_reports_filter()
            self.update_status("View saved reports", "white")
        elif index == 5:
            self.populate_dashboard_and_tables()
            self.update_status("Caution ! , Authorized Persons Only", "yellow", "#333333")
        elif index == 6:
            self.update_status("Thank You!", "white")

        if index in [2, 3]:
            self.ui.right_sidebar.show()
        else:
            self.ui.right_sidebar.hide()

    def delete_selected_user(self, *args):
        row = self.ui.users_table.currentRow()
        if row >= 0 and QMessageBox.question(self.ui, 'Confirm', 'Delete user?') == QMessageBox.StandardButton.Yes:
            self.ui.users_table.removeRow(row)

    def delete_selected_eq(self, *args):
        row = self.ui.maint_table.currentRow()
        if row >= 0 and QMessageBox.question(self.ui, 'Confirm', 'Delete equipment?') == QMessageBox.StandardButton.Yes:
            self.ui.maint_table.removeRow(row)

    def handle_save_users(self, *args):
        if QMessageBox.question(self.ui, 'Confirm', 'Save changes?') != QMessageBox.StandardButton.Yes: return
        data = []
        for r in range(self.ui.users_table.rowCount()):
            u_name = self.ui.users_table.item(r, 0).text() if self.ui.users_table.item(r, 0) else ""
            if not u_name.strip(): continue
            displayed_pwd = self.ui.users_table.item(r, 1).text() if self.ui.users_table.item(r, 1) else ""
            hidden_pwd = self.ui.users_table.item(r, 1).data(Qt.ItemDataRole.UserRole)
            pwd = displayed_pwd if displayed_pwd != "***" else hidden_pwd
            role = self.ui.users_table.cellWidget(r, 2).currentText()
            act = self.ui.users_table.cellWidget(r, 3).currentText()
            data.append({"User_Name": u_name, "Password": pwd, "Role": role, "Active": act})
        self.db.save_users(data)
        self.update_status("Users saved.", "white", "#4caf50")
        self.ui.user_combo.clear()
        self.ui.user_combo.addItems(self.db.get_users())
        self.populate_dashboard_and_tables()

    def handle_save_equipment(self, *args):
        if QMessageBox.question(self.ui, 'Confirm', 'Save equipment?') != QMessageBox.StandardButton.Yes: return
        data = []
        for r in range(self.ui.maint_table.rowCount()):
            eq_name = self.ui.maint_table.item(r, 0).text() if self.ui.maint_table.item(r, 0) else ""
            if not eq_name.strip(): continue
            ast_id = self.ui.maint_table.item(r, 1).text() if self.ui.maint_table.item(r, 1) else ""
            c_date = self.ui.maint_table.item(r, 2).text() if self.ui.maint_table.item(r, 2) else ""
            data.append({"Equipment_Name": eq_name, "Asset_ID": ast_id, "Cal_Due_Date": c_date, "Status": ""})
        self.db.save_equipment(data)
        self.update_status("Equipment saved.", "white", "#4caf50")
        self.populate_dashboard_and_tables()

    def handle_login(self, *args):
        is_valid, user_data = self.db.validate_login(self.ui.user_combo.currentText(), self.ui.pass_input.text())
        if is_valid:
            self.current_user = user_data
            role = self.current_user.get('Role', 'Operator').upper()

            for btn in self.ui.nav_buttons.values(): btn.show()
            self.ui.btn_toggle_right.show()
            self.ui.btn_start_tune.show()

            if role == "OPERATOR":
                self.ui.nav_buttons['maint'].hide()
            elif role == "QA":
                self.ui.nav_buttons['tune'].hide()
                self.ui.nav_buttons['cal'].hide()
                self.ui.nav_buttons['maint'].hide()
                self.ui.btn_toggle_right.hide()
                self.ui.btn_start_tune.hide()

            self.ui.left_sidebar.show()
            self.ui.logout_btn.show()
            self.ui.home_btn.show()
            self.session_time = QTime(0, 0, 0)
            self.session_timer.start(1000)
            self.navigate_to(1, 'home')
        else:
            QMessageBox.warning(self.ui, "Login Failed", "Incorrect password or User Inactive.")

    def handle_logout(self, *args):
        self.current_user = None
        self.ui.left_sidebar.hide()
        self.ui.right_sidebar.hide()
        self.ui.logout_btn.hide()
        self.ui.home_btn.hide()
        self.ui.user_info_label.setText("")
        self.session_timer.stop()
        self.ui.pass_input.clear()
        self.update_status("Successfully logged Out", "white")
        self.ui.stacked_widget.setCurrentIndex(0)

    # --- CALIBRATION LOGIC (STATE MACHINE) ---
    def create_massive_popup(self, title, message, btn_text):
        if self.cal_popup:
            try:
                self.cal_popup.close()
            except:
                pass
        self.cal_popup = QMessageBox(self.ui)
        self.cal_popup.setWindowTitle(title)
        self.cal_popup.setText(message)
        self.cal_popup.setStyleSheet("""
            QMessageBox { background-color: #252526; }
            QLabel { color: white; font-size: 18px; font-weight: bold; min-width: 700px; min-height: 60px; }
            QPushButton { background-color: #0d47a1; color: white; font-size: 18px; padding: 15px 30px; border-radius: 8px; min-width: 200px; }
            QPushButton:hover { background-color: #1565c0; }
        """)
        btn = self.cal_popup.addButton(btn_text, QMessageBox.ButtonRole.ActionRole)
        self.cal_popup.setWindowModality(Qt.WindowModality.NonModal)
        return btn

    def log_cal(self, msg, color="white"):
        self.ui.cal_log_window.append(f"<span style='color:{color}'>{msg}</span>")

    def handle_start_cal(self, *args):
        self.vna.connect()
        if self.is_calibrating:
            self.vna.write(":SENS1:CORR:COLL:CLE")
            self.log_cal("Calibration Cancelled by user.", "red")
            self.reset_calibration()
            return

        self.is_calibrating = True
        self.ui.btn_start_cal.setText("CANCEL CALIBRATION")
        self.ui.btn_start_cal.setStyleSheet(
            "QPushButton { background-color: #b71c1c; color: white; font-size: 20px; font-weight: bold; padding: 20px; border-radius: 10px; border: none; }")
        self.cal_step = 0
        self.cal_pressed_indices.clear()

        self.vna.write(":SENS1:CORR:COLL:METH:SOLT2 1,2")
        self.log_cal("--- Starting 2-Port Calibration ---", "#00ffff")
        self.prompt_next_cal_step()

    def prompt_next_cal_step(self):
        if self.cal_step > 6:
            self.finish_calibration()
            return

        btn_idx = self.cal_sequence[self.cal_step]
        step_name = self.cal_names[btn_idx]

        btn = self.create_massive_popup(f"Step {self.cal_step + 1}", f"Connect {step_name}", f"Connect {step_name}")
        btn.clicked.connect(lambda checked=False: self.process_cal_step(btn_idx, is_manual=False))
        self.cal_popup.show()

    def process_cal_step(self, btn_idx, is_manual=False):
        if not self.is_calibrating and not is_manual: return

        self.cal_pressed_indices.add(btn_idx)
        cmds = self.cal_cmds[btn_idx].split('\n')
        expected_btn_idx = self.cal_sequence[self.cal_step] if self.cal_step <= 6 else -1

        def execute_sequence(cmd_list):
            if not cmd_list:
                self.ui.cal_btns[btn_idx].setStyleSheet("background-color: #4caf50; color: white;")
                self.ui.cal_lbls[btn_idx].setText("Done")
                self.ui.cal_lbls[btn_idx].setStyleSheet("color: #4caf50; font-weight: bold;")

                if self.cal_popup:
                    try:
                        self.cal_popup.close()
                    except:
                        pass

                if is_manual and btn_idx != expected_btn_idx:
                    self.log_cal(f"Manual Run: {self.cal_names[btn_idx]} ... Done", "orange")
                    if len(self.cal_pressed_indices) >= 7:
                        self.is_calibrating = False
                        self.finish_calibration()
                    return

                self.log_cal(f"{self.cal_names[btn_idx]} ... Done", "#4caf50")
                if not is_manual or (is_manual and btn_idx == expected_btn_idx):
                    self.cal_step += 1
                    QTimer.singleShot(500, self.prompt_next_cal_step)
                return

            current_cmd = cmd_list.pop(0)
            self.vna.write(current_cmd)

            if cmd_list:
                QTimer.singleShot(3000, lambda: execute_sequence(cmd_list))
            else:
                QTimer.singleShot(1000, lambda: execute_sequence([]))

        execute_sequence(cmds)

    def finish_calibration(self):
        self.log_cal("Saving Calibration... Please wait.", "#00ffff")

        def save_step_1():
            self.vna.write(":SENS1:CORR:COLL:SAVE")
            QTimer.singleShot(2500, save_step_2)

        def save_step_2():
            self.vna.write(":SENS1:CORR:STAT ON")
            QTimer.singleShot(1500, save_step_3)

        def save_step_3():
            stat = self.vna.query(":SENS1:CORR:STAT?")
            if stat == "1":
                self.log_cal("Calibration Status: PASS", "#4caf50")
                self.update_status("Verify Calibration", "white")
                self.val_step = 0
                self.val_passed_overall = True
                self.prompt_validation_step()
            else:
                self.log_cal("Calibration Status: FAIL", "red")
                self.reset_calibration()

        QTimer.singleShot(1500, save_step_1)

    def prompt_validation_step(self):
        if self.val_step >= len(self.val_sequence):
            self.validation_complete()
            return

        step = self.val_sequence[self.val_step]
        if self.cal_popup:
            try:
                self.cal_popup.close()
            except:
                pass

        self.cal_popup = QMessageBox(self.ui)
        self.cal_popup.setWindowTitle("Validation")
        self.cal_popup.setText(f"Connect {step['name']}")
        self.cal_popup.setStyleSheet("""
            QMessageBox { background-color: #252526; }
            QLabel { color: white; font-size: 18px; font-weight: bold; min-width: 400px; min-height: 60px; }
            QPushButton { background-color: #0d47a1; color: white; font-size: 18px; padding: 15px 30px; border-radius: 8px; min-width: 200px; }
            QPushButton:hover { background-color: #1565c0; }
        """)
        btn = self.cal_popup.addButton(f"Verify {step['name'].split()[0]}", QMessageBox.ButtonRole.ActionRole)
        self.cal_popup.setWindowModality(Qt.WindowModality.NonModal)
        btn.clicked.connect(lambda checked=False: self.process_validation_step())
        self.cal_popup.show()

    def process_validation_step(self):
        if self.cal_popup: self.cal_popup.close()
        step = self.val_sequence[self.val_step]
        step_name = step['name']
        param = step['param']

        self.log_cal(f"--- Verifying {step_name} ---", "#00ffff")

        self.vna.write(":CALC1:PAR:COUN 1")
        self.vna.write(f":CALC1:PAR1:DEF {param}")
        self.vna.write(":CALC1:FORM MLOG")
        self.vna.write(":INIT1:CONT OFF")
        self.vna.write(":INIT1:IMM")
        self.vna.query("*OPC?")

        if DEBUG_MODE:
            if "OPEN" in step_name or "SHORT" in step_name:
                val = -1.0
            elif "LOAD" in step_name:
                val = -45.0
            else:
                val = 0.1
        else:
            data = self.vna.query(":CALC1:DATA:FDAT?")
            try:
                val = min(map(float, data.split(',')))
            except:
                val = 999.9

        self.vna.write(":INIT1:CONT ON")

        passed = False
        limit_txt = ""
        if "OPEN" in step_name or "SHORT" in step_name:
            passed = val > -5
            limit_txt = "> -5 dB"
        elif "LOAD" in step_name:
            passed = val < -35
            limit_txt = "< -35 dB"
        elif "THRU" in step_name:
            passed = -0.5 < val < 0.5
            limit_txt = "±0.5 dB"

        if passed:
            self.log_cal(f"{step_name.split()[0]} Verified: {val:.2f} dB (Limit: {limit_txt}) - PASS", "#4caf50")
        else:
            self.log_cal(f"{step_name.split()[0]} Failed: {val:.2f} dB (Limit: {limit_txt}) - FAIL", "#f44336")
            self.val_passed_overall = False

        self.val_step += 1
        QTimer.singleShot(500, self.prompt_validation_step)

    def validation_complete(self):
        if self.cal_popup:
            try:
                self.cal_popup.close()
            except:
                pass

        self.cal_popup = QMessageBox(self.ui)
        if self.val_passed_overall:
            self.log_cal("Validation Sequence Complete. All PASS.", "#4caf50")
            self.cal_popup.setWindowTitle("Success")
            self.cal_popup.setText("Calibration & Validation Successful!")
            btn_text = "Back to Tune Window"
        else:
            self.log_cal("Validation Sequence FAILED. Please recalibrate.", "#f44336")
            self.cal_popup.setWindowTitle("Validation Failed")
            self.cal_popup.setText("Calibration validation failed limits. Please recalibrate.")
            btn_text = "Restart Calibration"

        self.cal_popup.setStyleSheet("""
            QMessageBox { background-color: #252526; }
            QLabel { color: white; font-size: 18px; font-weight: bold; min-width: 400px; min-height: 60px; }
            QPushButton { background-color: #0d47a1; color: white; font-size: 18px; padding: 15px 30px; border-radius: 8px; min-width: 200px; }
            QPushButton:hover { background-color: #1565c0; }
        """)
        btn = self.cal_popup.addButton(btn_text, QMessageBox.ButtonRole.ActionRole)
        self.cal_popup.setWindowModality(Qt.WindowModality.NonModal)

        if self.val_passed_overall:
            btn.clicked.connect(
                lambda checked=False: [self.reset_calibration(), self.navigate_to(2, 'tune', preserve_tune=True)])
        else:
            btn.clicked.connect(lambda checked=False: self.reset_calibration())

        self.cal_popup.show()

    def reset_calibration(self):
        self.is_calibrating = False
        self.cal_step = 0
        self.val_step = 0
        self.ui.btn_start_cal.setText("START CALIBRATION")
        self.ui.btn_start_cal.setStyleSheet(
            "QPushButton { background-color: #0d47a1; color: white; font-size: 20px; font-weight: bold; padding: 20px; border-radius: 10px; border: none; }")
        for btn, lbl in zip(self.ui.cal_btns, self.ui.cal_lbls):
            btn.setStyleSheet("")
            lbl.setText("")

    def clear_calibration_log(self, *args):
        self.ui.cal_log_window.clear()
        self.vna.write(":SENS1:CORR:COLL:CLE")
        self.log_cal("Calibration Cleared from VNA.", "red")
        self.reset_calibration()
        self.cal_pressed_indices.clear()

    # --- TUNE PAGE LOGIC (ASYNC VNA SETUP) ---
    def check_tune_top_ok(self, *args):
        if self.ui.pn_combo.currentText().strip() and self.ui.sn_input.text().strip() and self.ui.wo_combo.currentText().strip():
            self.ui.ok_top_btn.setEnabled(True)
        else:
            self.ui.ok_top_btn.setEnabled(False)

    def parse_atten_val(self, val, default=None):
        if not val or str(val).strip() == '': return default
        try:
            return -abs(float(str(val).replace('M', '').replace('dB', '').strip()))
        except:
            return default

    def handle_tune_top_ok(self, *args):
        pn = self.ui.pn_combo.currentText()
        sn = self.ui.sn_input.text()
        wo = self.ui.wo_combo.currentText()

        self.ui.ok_top_btn.setEnabled(False)
        self.update_status("Configuring VNA... Please wait.", "orange")

        self.vna.connect()
        details = self.db.get_part_details(pn)
        cmds = []

        if details:
            na_id = details.get('NA_SETUP_ID1', '').strip()
            if na_id:
                na_params = self.db.get_na_setup(na_id)
                if na_params:
                    cf_hz = float(na_params.get('CENTER FREQUENCY', 0) or 0)
                    sp_hz = float(na_params.get('SPAN', 0) or 0)
                    if cf_hz: self.ui.r_freq_in.setText(f"{cf_hz / 1e6:g}")
                    if sp_hz: self.ui.r_span_in.setText(f"{sp_hz / 1e6:g}")
                    if na_params.get('POWER'): self.ui.r_pow_in.setText(str(na_params['POWER']))
                    if na_params.get('POINT'): self.ui.points_cb.setCurrentText(str(na_params['POINT']))

                    if na_params.get('Measure1 S21=1') == '1':
                        self.ui.smat_cb.setCurrentText("S21")
                    else:
                        self.ui.smat_cb.setCurrentText("S11")

                    if na_params.get('Form1 Log =0') == '0': self.ui.plot_cb.setCurrentText("Log Mag")

                    m1_count = int(na_params.get('MARK1', 0) or 0)
                    if m1_count >= 1: self.ui.m1_track_cb.setCurrentText("OFF")
                    self.ui.m2_chk.setChecked(m1_count >= 2)
                    self.ui.m3_chk.setChecked(m1_count >= 3)

                    def parse_val(v):
                        if not v: return ""
                        return str(v).upper().replace('M', 'E6').replace('K', 'E3').replace('G', 'E9')

                    if na_params.get('CENTER FREQUENCY'): cmds.append(
                        f":SENS1:FREQ:CENT {parse_val(na_params['CENTER FREQUENCY'])}")
                    if na_params.get('SPAN'): cmds.append(f":SENS1:FREQ:SPAN {parse_val(na_params['SPAN'])}")
                    if na_params.get('POINT'): cmds.append(f":SENS1:SWE:POIN {na_params['POINT']}")
                    if na_params.get('IFBW'): cmds.append(f":SENS1:BWID {parse_val(na_params['IFBW'])}")
                    if na_params.get('POWER'): cmds.append(f":SOUR1:POW {na_params['POWER']}")

                    if na_params.get('Measure1 S21=1') == '1':
                        cmds.append(":CALC1:PAR1:DEF S21")
                    else:
                        cmds.append(":CALC1:PAR1:DEF S11")

                    avg = na_params.get('Average', '')
                    if avg:
                        cmds.append(":SENS1:AVER ON")
                        cmds.append(f":SENS1:AVER:COUN {avg}")
                    else:
                        cmds.append(":SENS1:AVER OFF")

                    cmds.append(":CALC1:MARK1 OFF")
                    cmds.append(":CALC1:MARK2 OFF")
                    cmds.append(":CALC1:MARK3 OFF")

                    if m1_count >= 1:
                        cmds.append(":CALC1:MARK1 ON")
                        if na_params.get('CENTER FREQUENCY'): cmds.append(
                            f":CALC1:MARK1:X {parse_val(na_params['CENTER FREQUENCY'])}")
                    if m1_count >= 2:
                        cmds.append(":CALC1:MARK2 ON")
                        if na_params.get('MARK2 Min=1') == '1':
                            cmds.append(":CALC1:MARK2:FUNC:TYPE MIN")
                            cmds.append(":CALC1:MARK2:FUNC:TRAC ON")
                    if m1_count >= 3:
                        cmds.append(":CALC1:MARK3 ON")
                        val3 = na_params.get('MARK3 Max =0', '')
                        if val3 == '1' or val3 == '0':
                            cmds.append(":CALC1:MARK3:FUNC:TYPE MAX")
                            cmds.append(":CALC1:MARK3:FUNC:TRAC ON")

        def send_next_cmd():
            if not cmds:
                self.finalize_tune_setup(pn, sn, wo)
                return
            cmd = cmds.pop(0)
            self.vna.write(cmd)
            QTimer.singleShot(250, send_next_cmd)

        if cmds:
            send_next_cmd()
        else:
            self.finalize_tune_setup(pn, sn, wo)

    def finalize_tune_setup(self, pn, sn, wo):
        incomplete = self.db.find_incomplete_report(pn, sn, wo)

        self.ui.pn_combo.setEnabled(False)
        self.ui.sn_input.setEnabled(False)
        self.ui.wo_combo.setEnabled(False)
        self.ui.btn_tune_cal.setEnabled(True)

        if incomplete:
            if QMessageBox.question(self.ui, 'Resume',
                                    'Found incomplete test. Continue from previous stages?') == QMessageBox.StandardButton.Yes:
                self.current_report_id = incomplete['ID']
                try:
                    h, m, s = map(int, incomplete.get('Spend_Hours', '0:0:0').split(':'))
                    self.tuning_seconds = h * 3600 + m * 60 + s
                except:
                    self.tuning_seconds = 0

                for i in range(4):
                    if incomplete.get(f'Freq{i + 1}Result') in ['PASS', 'FAIL']:
                        self.ui.tune_tabs.setTabEnabled(i, False)
                        if i + 1 < 4: self.ui.tune_tabs.setCurrentIndex(i + 1)
            else:
                self.current_report_id = None
                self.tuning_seconds = 0
                self.ui.test_time_lbl.setText(" Time: 00:00:00 ")
        else:
            self.current_report_id = None
            self.tuning_seconds = 0
            self.ui.test_time_lbl.setText(" Time: 00:00:00 ")

        self.ui.ok_top_btn.setStyleSheet(
            "QPushButton { background-color: #388e3c; color: white; border:none; padding: 6px 15px; }")

        current_stage = self.ui.stage_ui_elements[self.ui.tune_tabs.currentIndex()]
        current_stage['btn_leason'].setEnabled(True)
        current_stage['btn_leason'].setChecked(True)
        current_stage['btn_leason'].setText("START/STOP: ON")

        self.tuning_timer.start(1000)
        self.live_update_timer.start(800)
        self.update_status("Testing in progress...", "white", "#f57c00")

    def fetch_live_vna_data(self):
        if not self.vna.is_connected and not DEBUG_MODE:
            return

        if DEBUG_MODE:
            return

        current_idx = self.ui.tune_tabs.currentIndex()
        if current_idx >= len(self.ui.stage_ui_elements): return
        stage = self.ui.stage_ui_elements[current_idx]

        if not stage['btn_leason'].isChecked():
            return

        try:
            x_val = self.vna.query(":CALC1:MARK2:X?")
            if x_val:
                freq_mhz = float(x_val) / 1e6
                stage['m_input'].setText(f"{freq_mhz:.4f}")

            if stage['attn_frame'].isVisible():
                y_val = self.vna.query(":CALC1:MARK2:Y?")
                if y_val:
                    attn_db = float(y_val.split(',')[0])
                    stage['attn_m_input'].setText(f"{attn_db:.2f}")

        except Exception as e:
            pass

    def update_unit_title(self, text):
        if not text.strip(): return self.ui.unit_title_lbl.setText("<b>...</b>")

        self._is_updating = True
        try:
            details = self.db.get_part_details(text)
            if not details: return

            self.ui.unit_title_lbl.setText(f"<b>{details.get('CABLE_EXPLAIN', 'Unknown')}</b>")
            try:
                active_stages = int(details.get('STEP1_HowMany_ITEMS', 1))
            except ValueError:
                active_stages = 1

            fixed_caps, tuned_caps = self.db.get_capacitors()
            col_o_val = details.get('Atten Test ID N Window: Trace:Marker: X or YR or YI', '').strip()
            raw_attn_lsl = self.parse_atten_val(details.get('Atten HIGH', ''))

            for i, stage in enumerate(self.ui.stage_ui_elements):
                stage_num = i + 1
                self.ui.tune_tabs.setTabVisible(i, stage_num <= active_stages)
                stage['btn_confirm'].setText("Save/Next stage" if stage_num < active_stages else "Confirm")

                stage_name = details.get(f'Blun{stage_num} Name', f'Stage {stage_num}')
                stage['status_box'].setText(
                    f"<b>Test: {stage_name}</b><br>{details.get('Note1&&Note2', '').replace('&&', '<br>')}")

                def safe_float(key, default):
                    try:
                        return float(details.get(key, str(default)).replace('M', '').strip())
                    except:
                        return default

                stage['lsl'] = safe_float('Frequency Low', 63.68)
                stage['usl'] = safe_float('Frequency High', 63.88)
                span = stage['usl'] - stage['lsl']
                if span == 0: span = 1.0
                stage['lsl_lbl'].setText(f"{stage['lsl']}")
                stage['usl_lbl'].setText(f"{stage['usl']}")
                stage['lbl_min'].setText(f"{stage['lsl'] - (span * 0.5):.2f}")
                stage['lbl_max'].setText(f"{stage['usl'] + (span * 0.5):.2f}")

                # --- THE FIX: Hide entire Attenuation block if NA ---
                if col_o_val or raw_attn_lsl is not None:
                    stage['attn_frame'].setVisible(True)
                    stage['attn_frame'].setEnabled(True)
                    stage['attn_lsl'] = raw_attn_lsl if raw_attn_lsl is not None else -20.0
                    stage['attn_lsl_lbl'].setText(f"{stage['attn_lsl']}")
                    stage['attn_usl_lbl'].setText("")
                else:
                    stage['attn_frame'].setVisible(False)
                    stage['attn_frame'].setEnabled(False)
                    stage['attn_lsl'] = None
                    stage['attn_lsl_lbl'].setText("N/A")
                    stage['attn_usl_lbl'].setText("N/A")

                stage['opt1'].blockSignals(True)
                stage['opt2'].blockSignals(True)
                stage['opt1'].clear()
                stage['opt1'].addItems(fixed_caps)
                stage['opt1'].setCurrentIndex(-1)
                stage['opt2'].clear()
                stage['opt2'].addItems(tuned_caps)
                stage['opt2'].setCurrentIndex(-1)
                stage['opt1'].blockSignals(False)
                stage['opt2'].blockSignals(False)

                stage['stage_name'] = stage_name

        finally:
            self._is_updating = False

        self.check_tune_top_ok()

    def update_freq_graph(self, text, stage):
        if self._is_updating: return
        if not text.strip() or text in ['-', '.', '-.']:
            stage['spec_slider'].setValue(50)
            stage['spec_slider'].setStyleSheet(self.ui.base_slider_style % "#555555")
            return
        try:
            val = float(text)
            span = stage['usl'] - stage['lsl']
            if span == 0: span = 0.001
            min_val = stage['lsl'] - (span * 0.5)
            max_val = stage['usl'] + (span * 0.5)

            if max_val == min_val:
                pct = 50
            else:
                pct = int(((val - min_val) / (max_val - min_val)) * 100)

            clamped_pct = max(0, min(100, pct))
            stage['spec_slider'].setValue(clamped_pct)
            if stage['lsl'] <= val <= stage['usl']:
                stage['spec_slider'].setStyleSheet(self.ui.base_slider_style % "#4caf50")
            else:
                stage['spec_slider'].setStyleSheet(self.ui.base_slider_style % "#f44336")
        except ValueError:
            pass

    def update_attn_graph(self, text, stage):
        if self._is_updating: return
        if not text.strip() or text in ['-', '.', '-.']:
            stage['attn_slider'].setValue(-50)
            stage['attn_slider'].setStyleSheet(self.ui.vert_slider_style % "#555555")
            return
        try:
            val = float(text)
            lsl = stage['attn_lsl']
            if lsl is None: return

            clamped_val = max(-100.0, min(0.0, val))
            flipped_val = int(-100 - clamped_val)
            stage['attn_slider'].setValue(flipped_val)

            if -100 <= val <= lsl:
                stage['attn_slider'].setStyleSheet(self.ui.vert_slider_style % "#4caf50")
            else:
                stage['attn_slider'].setStyleSheet(self.ui.vert_slider_style % "#f44336")
        except ValueError:
            pass

    def clear_tune_data(self, full=True, preserve_status=False, *args):
        self._is_updating = True
        try:
            self.tuning_timer.stop()
            self.live_update_timer.stop()
            self.tuning_seconds = 0
            self.ui.test_time_lbl.setText(" Time: 00:00:00 ")
            self.current_report_id = None

            self.ui.pn_combo.setEnabled(True)
            self.ui.sn_input.setEnabled(True)
            self.ui.wo_combo.setEnabled(True)
            self.ui.btn_tune_cal.setEnabled(False)

            if full:
                self.ui.pn_combo.clearEditText()
                self.ui.pn_combo.setCurrentIndex(-1)
                self.ui.wo_combo.clearEditText()
                self.ui.wo_combo.setCurrentIndex(-1)
                self.ui.sn_input.clear()
                self.ui.ok_top_btn.setEnabled(False)
            else:
                self.ui.ok_top_btn.setEnabled(True)
                self.ui.ok_top_btn.setStyleSheet("padding: 6px 15px;")

            self.ui.unit_title_lbl.setText("<b>...</b>")

            for i, stage in enumerate(self.ui.stage_ui_elements):
                self.ui.tune_tabs.setTabEnabled(i, True)
                stage['m_input'].clear()
                stage['attn_m_input'].clear()
                stage['opt1'].setCurrentIndex(-1)
                stage['opt2'].setCurrentIndex(-1)

                stage['btn_leason'].setChecked(False)
                stage['btn_leason'].setEnabled(False)
                stage['btn_leason'].setText("START/STOP: OFF")

                stage['btn_confirm'].setChecked(False)
                stage['btn_confirm'].setEnabled(False)
                stage['btn_confirm'].setStyleSheet("padding: 12px;")

        finally:
            self._is_updating = False

        if not preserve_status:
            self.update_status("Enter Unit Details", "white")
        self.ui.tune_tabs.setCurrentIndex(0)

    def handle_retest(self, *args):
        self.clear_tune_data(full=False)

    def handle_tune_confirm(self, stage_dict):
        self.tuning_timer.stop()
        self.live_update_timer.stop()

        m = stage_dict['m_input']
        stage_idx = self.ui.tune_tabs.currentIndex() + 1
        active_stages = 1
        details = self.db.get_part_details(self.ui.pn_combo.currentText())
        if details:
            try:
                active_stages = int(details.get('STEP1_HowMany_ITEMS', 1))
            except:
                pass

        is_final_stage = stage_idx >= active_stages
        lsl, usl = stage_dict.get('lsl', 63.68), stage_dict.get('usl', 63.88)

        freq_res = "FAIL"
        try:
            if lsl <= float(m.text()) <= usl: freq_res = "PASS"
        except:
            pass

        attn_tested = stage_dict['attn_frame'].isVisible()

        # --- THE FIX: Blank string instead of "NA" ---
        attn_res = ""
        if attn_tested:
            attn_res = "FAIL"
            al = stage_dict['attn_lsl']
            try:
                if -100.0 <= float(stage_dict['attn_m_input'].text()) <= al: attn_res = "PASS"
            except:
                pass

        overall_pass = (freq_res == "PASS" and attn_res in ["PASS", ""])
        color_hex = "#4caf50" if overall_pass else "#f44336"

        pn = self.ui.pn_combo.currentText()
        sn = self.ui.sn_input.text()
        wo = self.ui.wo_combo.currentText()
        desc = self.ui.unit_title_lbl.text().replace('<b>', '').replace('</b>', '')
        stage_name = stage_dict.get('stage_name', f'Stage {stage_idx}')

        if is_final_stage:
            record_status = "PASS" if overall_pass else "FAIL"
            footer_status = f"Unit {record_status}!"
            popup_status = record_status
        else:
            record_status = "INCOMPLETE"
            footer_status = "PASS, Continue Next stage" if overall_pass else "FAIL, Stage Failed"
            popup_status = "Partial Pass" if overall_pass else "Fail"

        self.update_status(footer_status, "white", color_hex)

        stage_widget = self.ui.tune_tabs.widget(stage_idx - 1)
        chk_report = None
        for cb in stage_widget.findChildren(QCheckBox):
            if cb.text() == "Open Report":
                chk_report = cb
                break

        if chk_report and chk_report.isChecked():
            report_msg = f"<h3>Detailed Stage Report</h3>"
            report_msg += f"<b>Part Number:</b> {pn}<br>"
            report_msg += f"<b>Serial Number:</b> {sn}<br>"
            report_msg += f"<b>Work Order:</b> {wo}<br>"
            report_msg += f"<b>Description:</b> {desc}<br>"
            report_msg += f"<b>Stage Tested:</b> {stage_name}<br><hr>"
            report_msg += f"<b>Frequency Measured:</b> {m.text()} MHz (LSL: {lsl} | USL: {usl}) - <b>{freq_res}</b><br>"
            if attn_tested:
                report_msg += f"<b>Attenuation Measured:</b> {stage_dict['attn_m_input'].text()} dB (LSL: {stage_dict['attn_lsl']} dB) - <b>{attn_res}</b><br>"

            report_msg += f"<hr><b>Overall Stage Status:</b> <span style='color:{color_hex}'>{popup_status.upper()}</span>"

            msg_box = QMessageBox(self.ui)
            msg_box.setWindowTitle(f"Test Report - {sn}")
            msg_box.setTextFormat(Qt.TextFormat.RichText)
            msg_box.setText(report_msg)
            msg_box.setStyleSheet(
                "QMessageBox { background-color: #252526; color: white; } QLabel { font-size: 14px; min-width: 350px; } QPushButton { background-color: #0d47a1; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold; }")
            msg_box.exec()

        stage_dict['btn_confirm'].setStyleSheet(
            f"QPushButton {{ background-color: {color_hex}; color: white; border:none; padding: 12px; }}")
        stage_dict['btn_leason'].setChecked(False)
        stage_dict['btn_leason'].setText("START/STOP: OFF")

        h, rem = divmod(self.tuning_seconds, 3600)
        m_time, s_time = divmod(rem, 60)

        # --- THE FIX: DYNAMICALLY FIND VNA ASSET ID ---
        vna_asset = ""
        for eq in self.db.get_equipment():
            name = eq.get('Equipment_Name', '').upper()
            if 'VNA' in name or 'E5061' in name or 'NETWORK ANALYZER' in name:
                vna_asset = eq.get('Asset_ID', '')
                break

        record = {
            "ID": self.current_report_id,
            "Tuning_Date": QDateTime.currentDateTime().toString("yyyy-MM-dd"),
            "Tuning_Time": QDateTime.currentDateTime().toString("HH:mm:ss"),
            "PN": pn,
            "SL": sn,
            "WO": wo,
            "Descrip": desc,
            "User": self.current_user.get('User_Name', 'Unknown') if self.current_user else 'Unknown',
            "Spend_Hours": f"{h}:{m_time:02d}:{s_time:02d}",
            "NA": vna_asset,
            f"Stage{stage_idx}": stage_name,
            f"Freq{stage_idx}Low": lsl,
            f"Freq{stage_idx}High": usl,
            f"Freq{stage_idx}Data": m.text(),
            f"Freq{stage_idx}Result": freq_res,
            f"Attn{stage_idx}Low": stage_dict['attn_lsl'] if attn_res != "" else "",
            f"Attn{stage_idx}High": "",
            f"Attn{stage_idx}Data": stage_dict['attn_m_input'].text() if attn_res != "" else "",
            f"Attn{stage_idx}Result": attn_res,
            "Result": record_status
        }

        self.current_report_id = self.db.save_or_update_report(record)

        if not is_final_stage:
            self.ui.tune_tabs.setTabEnabled(stage_idx - 1, False)
            self.ui.tune_tabs.setCurrentIndex(stage_idx)
            next_stage = self.ui.stage_ui_elements[stage_idx]
            next_stage['btn_leason'].setEnabled(True)
            next_stage['btn_leason'].setChecked(True)
            next_stage['btn_leason'].setText("START/STOP: ON")
            self.tuning_timer.start(1000)
            self.live_update_timer.start(800)
        else:
            self.live_update_timer.stop()
            QTimer.singleShot(2000, lambda: self.clear_tune_data(full=False, preserve_status=True))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = MainController()
    sys.exit(app.exec())