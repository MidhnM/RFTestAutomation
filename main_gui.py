from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QStackedWidget, QGridLayout,
                             QComboBox, QTableWidget, QTableWidgetItem, QTabWidget, QFrame,
                             QMessageBox, QCheckBox, QTextBrowser, QSlider, QHeaderView, QAbstractItemView, QDateEdit,
                             QFormLayout)
from PyQt6.QtCore import Qt, QTimer, QDate
from PyQt6.QtGui import QColor


class IndustrialUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Industrial Dashboard")
        self.setGeometry(100, 100, 1400, 850)
        self.apply_dark_theme()

        self.active_btn_style = "text-align: left; padding: 12px; background-color: #0d47a1; color: white; border-radius: 4px; font-weight: bold; font-size: 14px;"
        self.inactive_btn_style = "text-align: left; padding: 12px; background-color: transparent; color: #aaaaaa; border-radius: 4px; font-weight: bold; font-size: 14px;"

        self.init_ui()

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; color: #ffffff; }
            QWidget { background-color: #1e1e1e; color: #ffffff; font-family: 'Segoe UI', Arial; }
            QLabel { font-size: 14px; }
            QPushButton { background-color: #333333; color: white; border: 1px solid #444; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #555555; border: 1px solid #777; }
            QPushButton:pressed { background-color: #0d47a1; color: white; border: 1px solid #0d47a1; }
            QPushButton:disabled { background-color: #2a2a2a; color: #555555; border: 1px solid #333; }
            QPushButton:checked { background-color: #4caf50; color: white; border: 1px solid #4caf50; }
            QLineEdit, QTextBrowser, QDateEdit { background-color: #2d2d2d; border: 1px solid #777; padding: 6px; color: white; border-radius: 4px;}
            QComboBox { background-color: #333333; border: 1px solid #888; padding: 6px; color: white; border-radius: 4px; }
            QTableWidget { background-color: #252526; alternate-background-color: #2d2d2d; gridline-color: #555; }
            QHeaderView::section { background-color: #333; padding: 4px; border: 1px solid #555; font-weight: bold; }
            QTabBar::tab { background: #333; padding: 10px 20px; font-size: 14px; font-weight: bold; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px;}
            QTabBar::tab:selected { background: #0d47a1; color: white; }
        """)

    def init_ui(self):
        self.header_frame = QFrame()
        self.header_frame.setStyleSheet("background-color: #252526; border-bottom: 2px solid #333;")
        header_layout = QHBoxLayout(self.header_frame)
        self.company_label = QLabel("<b>PHILIPS</b> | Industrial Test System")
        self.datetime_label = QLabel("")
        self.user_info_label = QLabel("")
        self.logout_btn = QPushButton("Logout")
        self.logout_btn.setStyleSheet("QPushButton { background-color: #b71c1c; border:none; }")
        self.logout_btn.hide()
        header_layout.addWidget(self.company_label)
        header_layout.addStretch()
        header_layout.addWidget(self.datetime_label)
        header_layout.addStretch()
        header_layout.addWidget(self.user_info_label)
        header_layout.addWidget(self.logout_btn)

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.header_frame)

        middle_layout = QHBoxLayout()
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)
        self.setup_left_menu()
        middle_layout.addWidget(self.left_sidebar)
        self.stacked_widget = QStackedWidget()
        middle_layout.addWidget(self.stacked_widget)
        self.setup_right_menu()
        middle_layout.addWidget(self.right_sidebar)
        main_layout.addLayout(middle_layout)

        self.footer_frame = QFrame()
        self.footer_frame.setStyleSheet("background-color: #252526; border-top: 2px solid #333; padding: 10px;")
        footer_layout = QHBoxLayout(self.footer_frame)
        self.status_label = QLabel("Status: System Ready.")
        self.status_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: white; padding: 2px 6px; border-radius: 4px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.home_btn = QPushButton("EXIT to Home page")
        self.home_btn.setStyleSheet("QPushButton { background-color: #0d47a1; font-weight: bold; }")
        self.home_btn.hide()
        footer_layout.addStretch()
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()
        footer_layout.addWidget(self.home_btn)
        main_layout.addWidget(self.footer_frame)
        self.setCentralWidget(main_widget)

        self.create_login_page()
        self.create_home_page()
        self.create_tune_page()
        self.create_calibration_page()
        self.create_reports_page()
        self.create_maintenance_page()
        self.create_about_page()

    def setup_left_menu(self):
        self.left_sidebar = QFrame()
        self.left_sidebar.setStyleSheet("background-color: #252526; border-right: 1px solid #333;")
        self.left_sidebar.setFixedWidth(50)
        self.left_sidebar.hide()
        self.left_layout = QVBoxLayout(self.left_sidebar)
        self.left_layout.setContentsMargins(5, 15, 5, 15)
        self.left_layout.setSpacing(25)

        self.btn_toggle_left = QPushButton("☰")
        self.btn_toggle_left.setStyleSheet("background-color: transparent; border: none; font-size: 20px;")
        self.btn_toggle_left.clicked.connect(
            lambda *args: self.left_sidebar.setFixedWidth(200 if self.left_sidebar.width() == 50 else 50))
        self.left_layout.addWidget(self.btn_toggle_left, alignment=Qt.AlignmentFlag.AlignTop)

        self.nav_buttons = {}
        self.nav_buttons['home'] = QPushButton(" ⌂   Dashboard")
        self.nav_buttons['tune'] = QPushButton(" ⎈   Tune")
        self.nav_buttons['cal'] = QPushButton(" ⚖   Calibration")
        self.nav_buttons['reports'] = QPushButton(" ▤   Show Reports")
        self.nav_buttons['maint'] = QPushButton(" ⚙   Maintenance")

        for btn in self.nav_buttons.values():
            btn.setStyleSheet(self.inactive_btn_style)
            self.left_layout.addWidget(btn)

        self.left_layout.addStretch()
        self.nav_buttons['about'] = QPushButton(" ℹ   About")
        self.nav_buttons['about'].setStyleSheet(self.inactive_btn_style)
        self.left_layout.addWidget(self.nav_buttons['about'])

    def toggle_right_menu(self, *args):
        if self.right_sidebar.width() == 50:
            self.right_sidebar.setFixedWidth(280)
            self.right_controls.show()
        else:
            self.right_sidebar.setFixedWidth(50)
            self.right_controls.hide()

    def setup_right_menu(self):
        self.right_sidebar = QFrame()
        self.right_sidebar.setStyleSheet("background-color: #252526; border-left: 1px solid #333;")
        self.right_sidebar.setFixedWidth(50)
        self.right_sidebar.hide()

        self.right_layout = QVBoxLayout(self.right_sidebar)
        self.right_layout.setContentsMargins(5, 10, 5, 10)

        self.btn_toggle_right = QPushButton("⚙")
        self.btn_toggle_right.setStyleSheet("background-color: transparent; border: none; font-size: 18px;")
        self.btn_toggle_right.clicked.connect(self.toggle_right_menu)
        self.right_layout.addWidget(self.btn_toggle_right, alignment=Qt.AlignmentFlag.AlignTop)

        self.right_controls = QWidget()
        ctrl_layout = QVBoxLayout(self.right_controls)
        ctrl_layout.setContentsMargins(5, 10, 5, 0)
        ctrl_layout.setSpacing(12)

        ctrl_layout.addWidget(QLabel("<b>VNA Settings</b>"), alignment=Qt.AlignmentFlag.AlignCenter)

        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(10)

        self.plot_cb = QComboBox()
        self.plot_cb.addItems(["Log Mag", "Lin Mag", "Phase", "SWR", "Smith"])
        form_layout.addRow("Format:", self.plot_cb)

        self.smat_cb = QComboBox()
        self.smat_cb.addItems(["S11", "S21", "S12", "S22"])
        form_layout.addRow("S-Param:", self.smat_cb)

        self.r_freq_in = QLineEdit("1000")
        form_layout.addRow("Freq (MHz):", self.r_freq_in)

        self.r_span_in = QLineEdit("500")
        form_layout.addRow("Span (MHz):", self.r_span_in)

        self.r_pow_in = QLineEdit("0")
        form_layout.addRow("Power (dBm):", self.r_pow_in)

        self.points_cb = QComboBox()
        self.points_cb.addItems(["201", "401", "801", "1601", "3201"])
        form_layout.addRow("Points:", self.points_cb)

        ctrl_layout.addLayout(form_layout)

        self.btn_right_apply = QPushButton("Apply Setup")
        self.btn_right_apply.setStyleSheet("background-color: #388e3c; color: white;")
        ctrl_layout.addWidget(self.btn_right_apply)

        # MARKERS SECTION
        ctrl_layout.addWidget(QLabel("<b>Markers</b>"), alignment=Qt.AlignmentFlag.AlignCenter)

        m_form = QFormLayout()
        m_form.setVerticalSpacing(8)

        self.m1_track_cb = QComboBox()
        self.m1_track_cb.addItems(["OFF", "MAX (Peak)", "MIN (Dip)"])
        m_form.addRow("M1 Track:", self.m1_track_cb)

        self.m2_chk = QCheckBox("M2 (MHz):")
        self.m2_freq_in = QLineEdit()
        m_form.addRow(self.m2_chk, self.m2_freq_in)

        self.m3_chk = QCheckBox("M3 (MHz):")
        self.m3_freq_in = QLineEdit()
        m_form.addRow(self.m3_chk, self.m3_freq_in)

        ctrl_layout.addLayout(m_form)

        self.btn_clear_markers = QPushButton("Clear All Markers")
        self.btn_clear_markers.setStyleSheet("background-color: #b71c1c; color: white;")
        ctrl_layout.addWidget(self.btn_clear_markers)

        # BUTTONS SECTION
        self.btn_auto_scale = QPushButton("Auto Scale Graph")
        ctrl_layout.addWidget(self.btn_auto_scale)

        toggle_hbox = QHBoxLayout()
        self.avg_btn = QPushButton("Avg: OFF")
        self.avg_btn.setCheckable(True)
        self.rf_btn = QPushButton("RF: ON")
        self.rf_btn.setCheckable(True)
        self.rf_btn.setChecked(True)

        toggle_hbox.addWidget(self.avg_btn)
        toggle_hbox.addWidget(self.rf_btn)
        ctrl_layout.addLayout(toggle_hbox)

        ctrl_layout.addStretch()
        self.right_layout.addWidget(self.right_controls)
        self.right_controls.hide()

    def create_login_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        title_box = QWidget()
        t_layout = QVBoxLayout(title_box)
        t_layout.setContentsMargins(0, 60, 0, 0)
        comp_title = QLabel("THE COMPANY NAME")
        comp_title.setStyleSheet("font-size: 26px; color: #2596be; font-weight: bold;")
        comp_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_title = QLabel("Electronics Division")
        sub_title.setStyleSheet("font-size: 14px; color: #2596be;")
        sub_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t_layout.addWidget(comp_title)
        t_layout.addWidget(sub_title)
        layout.addWidget(title_box, alignment=Qt.AlignmentFlag.AlignTop)

        layout.addStretch()
        center_box = QWidget()
        center_box.setFixedWidth(350)
        center_layout = QVBoxLayout(center_box)
        title = QLabel("<h2>System Login</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.user_combo = QComboBox()
        self.user_combo.setStyleSheet("padding: 10px; font-size: 14px;")
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_btn = QPushButton("Login")
        self.login_btn.setStyleSheet(
            "QPushButton { background-color: #0d47a1; font-weight: bold; padding: 12px; font-size: 14px; border:none; }")

        center_layout.addWidget(title)
        center_layout.addWidget(self.user_combo)
        center_layout.addWidget(self.pass_input)
        center_layout.addWidget(self.login_btn)
        layout.addWidget(center_box, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()
        watermark = QLabel("© Midhun Madhu")
        watermark.setStyleSheet("color: #444444; font-size: 11px;")
        watermark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(watermark, alignment=Qt.AlignmentFlag.AlignBottom)
        self.stacked_widget.addWidget(page)

    def create_home_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        comp_title = QLabel("<h2>THE COMPANY NAME</h2>")
        comp_title.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        sub_title = QLabel("<i>Electronics Division</i>")
        sub_title.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        title = QLabel("<h1>Dashboard Home</h1>")
        title.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        layout.addWidget(comp_title);
        layout.addWidget(sub_title);
        layout.addWidget(title)

        stats_layout = QHBoxLayout()
        stat1 = QFrame()
        stat1.setStyleSheet("background-color: #252526; border-radius: 8px; border: 1px solid #555;")
        v1 = QVBoxLayout(stat1)
        v1.addWidget(QLabel("<b>Total Part Numbers Added</b>"), alignment=Qt.AlignmentFlag.AlignCenter)
        self.total_pn_lbl = QLabel("...")
        self.total_pn_lbl.setStyleSheet("font-size: 36px; color: #4caf50; font-weight: bold;")
        v1.addWidget(self.total_pn_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        stat2 = QFrame()
        stat2.setStyleSheet("background-color: #252526; border-radius: 8px; border: 1px solid #555;")
        v2 = QVBoxLayout(stat2)
        v2.addWidget(QLabel("<b>Total Tests Conducted</b>"), alignment=Qt.AlignmentFlag.AlignCenter)
        self.total_tests_lbl = QLabel("...")
        self.total_tests_lbl.setStyleSheet("font-size: 36px; color: #2196f3; font-weight: bold;")
        v2.addWidget(self.total_tests_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        stats_layout.addWidget(stat1);
        stats_layout.addWidget(stat2)
        layout.addLayout(stats_layout)

        layout.addSpacing(20)
        layout.addWidget(QLabel("<h3>Connected Equipment Status</h3>"))

        self.eq_table = QTableWidget(0, 4)
        self.eq_table.setHorizontalHeaderLabels(["Equipment Name", "Asset ID", "Calibration Due Date", "Status"])
        self.eq_table.horizontalHeader().setStretchLastSection(False)
        self.eq_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.eq_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.eq_table.setFixedHeight(180)

        table_layout = QHBoxLayout()
        table_layout.addWidget(self.eq_table);
        table_layout.addStretch()
        layout.addLayout(table_layout)

        layout.addStretch()
        self.btn_start_tune = QPushButton("START TUNING")
        self.btn_start_tune.setStyleSheet("""
            QPushButton { background-color: #0d47a1; color: white; font-size: 24px; font-weight: bold; padding: 25px; border-radius: 10px; border: none; }
        """)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch();
        btn_layout.addWidget(self.btn_start_tune, stretch=1);
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        self.stacked_widget.addWidget(page)

    def create_calibration_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        split_layout = QHBoxLayout()

        left_widget = QWidget()
        left_vbox = QVBoxLayout(left_widget)

        cal_title = QLabel("<h2>VNA Calibration</h2>")
        cal_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_vbox.addWidget(cal_title)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setVerticalSpacing(20)
        grid.setHorizontalSpacing(15)

        grid.addWidget(QLabel("<h3>Port 1</h3>"), 0, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(QLabel("<h3>Port 2</h3>"), 0, 2, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter)

        self.cal_btns, self.cal_lbls = [], []
        p1_names = ["Open 1", "Short 1", "Load 1"]
        p2_names = ["Open 2", "Short 2", "Load 2"]

        for i in range(3):
            b1 = QPushButton(p1_names[i]);
            b1.setFixedSize(120, 40);
            l1 = QLabel("")
            grid.addWidget(b1, i + 1, 0, alignment=Qt.AlignmentFlag.AlignRight)
            grid.addWidget(l1, i + 1, 1, alignment=Qt.AlignmentFlag.AlignLeft)
            self.cal_btns.append(b1);
            self.cal_lbls.append(l1)

            b2 = QPushButton(p2_names[i]);
            b2.setFixedSize(120, 40);
            l2 = QLabel("")
            grid.addWidget(b2, i + 1, 2, alignment=Qt.AlignmentFlag.AlignRight)
            grid.addWidget(l2, i + 1, 3, alignment=Qt.AlignmentFlag.AlignLeft)
            self.cal_btns.append(b2);
            self.cal_lbls.append(l2)

        self.btn_cal_thru = QPushButton("Through")
        self.btn_cal_thru.setFixedSize(160, 45)
        self.lbl_cal_thru = QLabel("")

        hbox_thru = QHBoxLayout()
        hbox_thru.addStretch();
        hbox_thru.addWidget(self.btn_cal_thru);
        hbox_thru.addWidget(self.lbl_cal_thru);
        hbox_thru.addStretch()
        grid.addLayout(hbox_thru, 4, 0, 1, 4)
        self.cal_btns.append(self.btn_cal_thru);
        self.cal_lbls.append(self.lbl_cal_thru)

        left_vbox.addWidget(grid_widget)
        left_vbox.addStretch()

        self.btn_start_cal = QPushButton("START CALIBRATION")
        self.btn_start_cal.setStyleSheet(
            "QPushButton { background-color: #0d47a1; color: white; font-size: 20px; font-weight: bold; padding: 20px; border-radius: 10px; border: none; }")
        left_vbox.addWidget(self.btn_start_cal)

        split_layout.addWidget(left_widget, stretch=1)

        right_widget = QWidget()
        right_vbox = QVBoxLayout(right_widget)

        log_header_layout = QHBoxLayout()
        log_header_layout.addWidget(QLabel("<h3>Calibration Status Log</h3>"))
        log_header_layout.addStretch()

        self.btn_clear_log = QPushButton("✕")
        self.btn_clear_log.setStyleSheet(
            "background: transparent; color: #d32f2f; font-size: 20px; font-weight: bold; border: none;")
        log_header_layout.addWidget(self.btn_clear_log)

        right_vbox.addLayout(log_header_layout)

        self.cal_log_window = QTextBrowser()
        self.cal_log_window.setStyleSheet(
            "background-color: #1e1e1e; color: #00ff00; font-family: monospace; font-size: 14px;")
        right_vbox.addWidget(self.cal_log_window)

        split_layout.addWidget(right_widget, stretch=1)

        layout.addLayout(split_layout)
        self.stacked_widget.addWidget(page)

    def create_tune_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.addWidget(QLabel("<h2>Tune Stage</h2>"))

        top_ctrl = QHBoxLayout()
        top_ctrl.addWidget(QLabel("Part Number:"))
        self.pn_combo = QComboBox();
        self.pn_combo.setEditable(True)
        top_ctrl.addWidget(self.pn_combo)

        top_ctrl.addSpacing(20);
        top_ctrl.addWidget(QLabel("Serial Number:"))
        self.sn_input = QLineEdit("")
        top_ctrl.addWidget(self.sn_input)

        top_ctrl.addSpacing(20);
        top_ctrl.addWidget(QLabel("Work Order:"))
        self.wo_combo = QComboBox();
        self.wo_combo.setEditable(True)
        top_ctrl.addWidget(self.wo_combo)

        top_ctrl.addSpacing(20)
        self.ok_top_btn = QPushButton("OK")
        self.ok_top_btn.setStyleSheet("padding: 6px 15px;")
        self.ok_top_btn.setEnabled(False)
        top_ctrl.addWidget(self.ok_top_btn)

        self.clear_btn = QPushButton("✕")
        self.clear_btn.setStyleSheet(
            "background: transparent; color: #d32f2f; font-size: 20px; font-weight: bold; border: none;")
        top_ctrl.addWidget(self.clear_btn)

        top_ctrl.addStretch()

        self.btn_tune_cal = QPushButton("Calibrate")
        self.btn_tune_cal.setStyleSheet("""
            QPushButton { background-color: #f57c00; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px; }
            QPushButton:disabled { background-color: #444444; color: #888888; }
        """)
        self.btn_tune_cal.setEnabled(False)
        top_ctrl.addWidget(self.btn_tune_cal)

        layout.addLayout(top_ctrl)

        layout.addSpacing(10)
        self.unit_title_lbl = QLabel("<b>...</b>")
        self.unit_title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.unit_title_lbl.setStyleSheet(
            "font-size: 20px; color: #2196f3; background-color: #252526; padding: 10px; border-radius: 5px;")
        layout.addWidget(self.unit_title_lbl)

        self.tune_tabs = QTabWidget()
        self.test_time_lbl = QLabel(" Time: 00:00:00 ")
        self.test_time_lbl.setStyleSheet(
            "font-size: 14px; font-weight: bold; background-color: #0d47a1; color: white; padding: 4px 10px; border-radius: 4px; margin-left: 10px;")
        self.tune_tabs.setCornerWidget(self.test_time_lbl, Qt.Corner.TopRightCorner)

        self.stage_ui_elements = []

        for i in range(1, 5):
            stage_widget = QWidget()
            stage_main_vbox = QVBoxLayout(stage_widget)
            stage_main_vbox.setContentsMargins(15, 10, 15, 10)

            status_box = QTextBrowser()
            status_box.setText(f"<b>Test: Stage {i}</b><br>- Awaiting Input...")
            status_box.setFixedHeight(80)
            stage_main_vbox.addWidget(status_box)

            split_hbox = QHBoxLayout()

            freq_frame = QFrame()
            freq_vbox = QVBoxLayout(freq_frame)
            freq_vbox.addWidget(QLabel("<b>Frequency Resonance test</b>"), alignment=Qt.AlignmentFlag.AlignCenter)

            scale_layout = QHBoxLayout()
            lbl_min = QLabel("...");
            lbl_lsl_scale = QLabel("LSL");
            lbl_target = QLabel("Target");
            lbl_usl_scale = QLabel("USL");
            lbl_max = QLabel("...")
            lbl_min.setAlignment(Qt.AlignmentFlag.AlignLeft);
            lbl_lsl_scale.setAlignment(Qt.AlignmentFlag.AlignCenter);
            lbl_target.setAlignment(Qt.AlignmentFlag.AlignCenter);
            lbl_usl_scale.setAlignment(Qt.AlignmentFlag.AlignCenter);
            lbl_max.setAlignment(Qt.AlignmentFlag.AlignRight)
            scale_layout.addWidget(lbl_min, stretch=1);
            scale_layout.addWidget(lbl_lsl_scale, stretch=1);
            scale_layout.addWidget(lbl_target, stretch=1);
            scale_layout.addWidget(lbl_usl_scale, stretch=1);
            scale_layout.addWidget(lbl_max, stretch=1)
            freq_vbox.addLayout(scale_layout)

            spec_slider = QSlider(Qt.Orientation.Horizontal)
            spec_slider.setRange(0, 100);
            spec_slider.setValue(50)
            spec_slider.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.base_slider_style = """QSlider::groove:horizontal { border: 1px solid #777; height: 10px; background: #2d2d2d; border-radius: 5px; } QSlider::handle:horizontal { background: %s; border: 2px solid white; width: 16px; margin: -5px 0; border-radius: 8px; }"""
            spec_slider.setStyleSheet(self.base_slider_style % "#4caf50")
            freq_vbox.addWidget(spec_slider)

            measure_row = QHBoxLayout()
            lsl_box = QVBoxLayout();
            lsl_title = QLabel("LSL");
            lsl_title.setAlignment(Qt.AlignmentFlag.AlignCenter);
            lsl_title.setStyleSheet("font-weight: bold; color: #aaaaaa; font-size: 13px;");
            lsl_lbl = QLabel("...");
            lsl_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter);
            lsl_lbl.setStyleSheet(
                "font-weight: bold; font-size: 16px; background-color: #252526; padding: 10px; border-radius: 4px;");
            lsl_box.addWidget(lsl_title);
            lsl_box.addWidget(lsl_lbl)
            m_box = QVBoxLayout();
            m_title = QLabel("Measured Value");
            m_title.setAlignment(Qt.AlignmentFlag.AlignCenter);
            m_title.setStyleSheet("font-weight: bold; color: #aaaaaa; font-size: 13px;");
            m_input = QLineEdit();
            m_input.setAlignment(Qt.AlignmentFlag.AlignCenter);
            m_input.setStyleSheet("font-size: 16px; padding: 10px;");
            m_box.addWidget(m_title);
            m_box.addWidget(m_input)
            usl_box = QVBoxLayout();
            usl_title = QLabel("USL");
            usl_title.setAlignment(Qt.AlignmentFlag.AlignCenter);
            usl_title.setStyleSheet("font-weight: bold; color: #aaaaaa; font-size: 13px;");
            usl_lbl = QLabel("...");
            usl_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter);
            usl_lbl.setStyleSheet(
                "font-weight: bold; font-size: 16px; background-color: #252526; padding: 10px; border-radius: 4px;");
            usl_box.addWidget(usl_title);
            usl_box.addWidget(usl_lbl)
            measure_row.addLayout(lsl_box, stretch=1);
            measure_row.addSpacing(10);
            measure_row.addLayout(m_box, stretch=1);
            measure_row.addSpacing(10);
            measure_row.addLayout(usl_box, stretch=1)
            freq_vbox.addLayout(measure_row)

            split_hbox.addWidget(freq_frame, stretch=2)
            split_hbox.addSpacing(40)

            # --- ATTENUATION FRAME (LSL IS TOP, USL IS BOTTOM) ---
            attn_frame = QFrame()
            attn_vbox = QVBoxLayout(attn_frame)
            attn_vbox.addWidget(QLabel("<b>Attenuation Stage</b>"), alignment=Qt.AlignmentFlag.AlignCenter)

            attn_content_hbox = QHBoxLayout()
            attn_slider_vbox = QVBoxLayout()
            attn_slider_vbox.addWidget(QLabel("0"), alignment=Qt.AlignmentFlag.AlignCenter)
            attn_slider = QSlider(Qt.Orientation.Vertical)
            attn_slider.setRange(-100, 0);
            attn_slider.setValue(-50)
            attn_slider.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.vert_slider_style = """QSlider::groove:vertical { border: 1px solid #777; width: 10px; background: #2d2d2d; border-radius: 5px; } QSlider::handle:vertical { background: %s; border: 2px solid white; height: 16px; margin: 0 -5px; border-radius: 8px; }"""
            attn_slider.setStyleSheet(self.vert_slider_style % "#4caf50")
            attn_slider_vbox.addWidget(attn_slider, alignment=Qt.AlignmentFlag.AlignCenter)
            attn_slider_vbox.addWidget(QLabel("-100"), alignment=Qt.AlignmentFlag.AlignCenter)
            attn_content_hbox.addLayout(attn_slider_vbox)

            attn_meas_vbox = QVBoxLayout()
            attn_lsl_title = QLabel("LSL");
            attn_lsl_title.setAlignment(Qt.AlignmentFlag.AlignCenter);
            attn_lsl_title.setStyleSheet("font-weight: bold; color: #aaaaaa; font-size: 13px;")
            attn_lsl_lbl = QLabel("...");
            attn_lsl_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter);
            attn_lsl_lbl.setStyleSheet("background-color: #252526; padding: 5px; border-radius: 4px;")
            attn_m_title = QLabel("Measured");
            attn_m_title.setAlignment(Qt.AlignmentFlag.AlignCenter);
            attn_m_title.setStyleSheet("font-weight: bold; color: #aaaaaa; font-size: 13px;")
            attn_m_input = QLineEdit();
            attn_m_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
            attn_usl_title = QLabel("USL");
            attn_usl_title.setAlignment(Qt.AlignmentFlag.AlignCenter);
            attn_usl_title.setStyleSheet("font-weight: bold; color: #aaaaaa; font-size: 13px;")
            attn_usl_lbl = QLabel("");
            attn_usl_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter);
            attn_usl_lbl.setStyleSheet("background-color: #252526; padding: 5px; border-radius: 4px; color: #777;")

            attn_meas_vbox.addStretch()
            attn_meas_vbox.addWidget(attn_lsl_title);
            attn_meas_vbox.addWidget(attn_lsl_lbl);
            attn_meas_vbox.addSpacing(10)
            attn_meas_vbox.addWidget(attn_m_title);
            attn_meas_vbox.addWidget(attn_m_input);
            attn_meas_vbox.addSpacing(10)
            attn_meas_vbox.addWidget(attn_usl_title);
            attn_meas_vbox.addWidget(attn_usl_lbl);
            attn_meas_vbox.addStretch()

            attn_content_hbox.addLayout(attn_meas_vbox)
            attn_vbox.addLayout(attn_content_hbox)
            split_hbox.addWidget(attn_frame, stretch=1)
            stage_main_vbox.addLayout(split_hbox)

            stage_main_vbox.addSpacing(30)

            cap_row = QHBoxLayout()
            cap_row.addWidget(QLabel("Fixed Capacitor pF:"))
            opt1_combo = QComboBox();
            opt1_combo.setEditable(True);
            opt1_combo.setFixedWidth(100)
            cap_row.addWidget(opt1_combo)
            cap_row.addSpacing(20)
            cap_row.addWidget(QLabel("Tunned Capacitor pF:"))
            opt2_combo = QComboBox();
            opt2_combo.setEditable(True);
            opt2_combo.setFixedWidth(100)
            cap_row.addWidget(opt2_combo)
            cap_row.addSpacing(15)

            action_lbl = QLabel(
                "<b>try adding text Add 2pF</b><br><span style='font-size: 12px; font-weight: normal; color: #aaaaaa;'>* Just for tuning purpose, not necessary to fill</span>")
            action_lbl.setStyleSheet("color: white; font-size: 16px;")
            cap_row.addWidget(action_lbl)
            cap_row.addStretch()

            stage_main_vbox.addLayout(cap_row)
            stage_main_vbox.addStretch(1)

            bot_btn_layout = QHBoxLayout()
            btn_retest = QPushButton("Retest")
            btn_retest.setStyleSheet("QPushButton { background-color: #f57c00; border:none; padding: 12px; }")
            btn_leason = QPushButton("START/STOP: OFF")
            btn_leason.setCheckable(True);
            btn_leason.setEnabled(False)
            btn_leason.setStyleSheet("padding: 12px;")
            btn_confirm = QPushButton("Save/Next stage")
            btn_confirm.setCheckable(True);
            btn_confirm.setEnabled(False);
            btn_confirm.setStyleSheet("padding: 12px;")

            # FIX: Auto-Check "Open Report" box by default
            chk_report = QCheckBox("Open Report")
            chk_report.setChecked(True)

            btn_print = QPushButton("Print")
            btn_print.setStyleSheet("padding: 12px;")

            bot_btn_layout.addWidget(btn_retest);
            bot_btn_layout.addStretch();
            bot_btn_layout.addWidget(btn_leason);
            bot_btn_layout.addSpacing(15)
            bot_btn_layout.addWidget(btn_confirm);
            bot_btn_layout.addSpacing(15);
            bot_btn_layout.addWidget(chk_report);
            bot_btn_layout.addStretch();
            bot_btn_layout.addWidget(btn_print)

            stage_main_vbox.addLayout(bot_btn_layout)

            stage_dict = {
                'm_input': m_input, 'opt1': opt1_combo, 'opt2': opt2_combo,
                'attn_frame': attn_frame, 'attn_m_input': attn_m_input,
                'attn_usl_lbl': attn_usl_lbl, 'attn_lsl_lbl': attn_lsl_lbl,
                'attn_slider': attn_slider, 'spec_slider': spec_slider,
                'btn_leason': btn_leason, 'btn_confirm': btn_confirm, 'btn_retest': btn_retest, 'btn_print': btn_print,
                'status_box': status_box, 'action_lbl': action_lbl, 'lsl_lbl': lsl_lbl, 'usl_lbl': usl_lbl,
                'lbl_min': lbl_min, 'lbl_max': lbl_max,
                'lsl': 63.68, 'usl': 63.88, 'attn_lsl': None
            }

            self.tune_tabs.addTab(stage_widget, f" Stage {i} ")
            self.stage_ui_elements.append(stage_dict)

        layout.addWidget(self.tune_tabs)
        self.stacked_widget.addWidget(page)

    def create_reports_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h2>Tested Data Reports</h2>"))

        filter_layout = QHBoxLayout()
        self.flt_date_start = QDateEdit(QDate.currentDate().addDays(-30))
        self.flt_date_start.setCalendarPopup(True)
        self.flt_date_end = QDateEdit(QDate.currentDate())
        self.flt_date_end.setCalendarPopup(True)

        self.flt_user = QComboBox();
        self.flt_user.addItem("All Users")
        self.flt_pn = QComboBox();
        self.flt_pn.addItem("All Parts")
        self.flt_wo = QLineEdit();
        self.flt_wo.setPlaceholderText("Work Order...")
        self.flt_status = QComboBox();
        self.flt_status.addItems(["All", "PASS", "FAIL", "INCOMPLETE"])

        self.btn_apply_filter = QPushButton("Apply Filter")
        self.btn_apply_filter.setStyleSheet("background-color: #0d47a1; padding: 6px 15px;")
        self.btn_clear_filter = QPushButton("✕")
        self.btn_clear_filter.setStyleSheet(
            "background: transparent; color: #d32f2f; font-size: 20px; font-weight: bold; border: none;")
        self.btn_export_csv = QPushButton("Print (CSV)")
        self.btn_export_csv.setStyleSheet("background-color: #388e3c; padding: 6px 15px;")

        filter_layout.addWidget(QLabel("From:"));
        filter_layout.addWidget(self.flt_date_start)
        filter_layout.addWidget(QLabel("To:"));
        filter_layout.addWidget(self.flt_date_end)
        filter_layout.addWidget(self.flt_user);
        filter_layout.addWidget(self.flt_pn);
        filter_layout.addWidget(self.flt_wo);
        filter_layout.addWidget(self.flt_status)
        filter_layout.addWidget(self.btn_apply_filter);
        filter_layout.addWidget(self.btn_clear_filter)
        filter_layout.addSpacing(20);
        filter_layout.addWidget(self.btn_export_csv)
        layout.addLayout(filter_layout)

        self.reports_table = QTableWidget(0, 59)
        self.report_headers = [
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
        self.reports_table.setHorizontalHeaderLabels(self.report_headers)
        self.reports_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.reports_table.horizontalHeader().setStretchLastSection(False)
        self.reports_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.reports_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.reports_table.setSortingEnabled(True)
        layout.addWidget(self.reports_table)
        self.stacked_widget.addWidget(page)

    def create_maintenance_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h2>Asset & Maintenance Management</h2>"))
        layout.addWidget(QLabel("<h3>User Management</h3>"))
        self.users_table = QTableWidget(0, 4)
        self.users_table.setHorizontalHeaderLabels(["Username", "Password", "Role", "Active"])
        self.users_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.users_table)

        user_btns = QHBoxLayout()
        self.btn_add_user = QPushButton("Add Blank Row");
        self.btn_del_user = QPushButton("Delete Selected");
        self.btn_del_user.setStyleSheet("background-color: #b71c1c;")
        self.btn_save_user = QPushButton("Save Users");
        self.btn_save_user.setStyleSheet("background-color: #388e3c;")
        user_btns.addWidget(self.btn_add_user);
        user_btns.addWidget(self.btn_del_user);
        user_btns.addStretch();
        user_btns.addWidget(self.btn_save_user)
        layout.addLayout(user_btns)

        layout.addSpacing(20)
        layout.addWidget(QLabel("<h3>Equipment Management</h3>"))
        self.maint_table = QTableWidget(0, 4)
        self.maint_table.setHorizontalHeaderLabels(
            ["Equipment Name", "Asset ID", "Calibration Due Date (yyyy-mm-dd)", "Status"])
        self.maint_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.maint_table)

        eq_btns = QHBoxLayout()
        self.btn_add_eq = QPushButton("Add Blank Row");
        self.btn_del_eq = QPushButton("Delete Selected");
        self.btn_del_eq.setStyleSheet("background-color: #b71c1c;")
        self.btn_save_eq = QPushButton("Save Equipment");
        self.btn_save_eq.setStyleSheet("background-color: #388e3c;")
        eq_btns.addWidget(self.btn_add_eq);
        eq_btns.addWidget(self.btn_del_eq);
        eq_btns.addStretch();
        eq_btns.addWidget(self.btn_save_eq)
        layout.addLayout(eq_btns)
        self.stacked_widget.addWidget(page)

    def create_about_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        about_box = QWidget()
        about_layout = QVBoxLayout(about_box)
        about_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(QLabel("<h2>About This Dashboard</h2>"), alignment=Qt.AlignmentFlag.AlignCenter)
        self.lbl_version = QLabel("<b>Application Version:</b> 1.0.21")
        about_layout.addWidget(self.lbl_version, alignment=Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(QLabel("<b>Developer:</b> Test Engineering Team"),
                               alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(about_box, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()
        watermark = QLabel("© Midhun Madhu")
        watermark.setStyleSheet("color: #444444; font-size: 11px;")
        watermark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(watermark, alignment=Qt.AlignmentFlag.AlignBottom)

        self.stacked_widget.addWidget(page)