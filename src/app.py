import asyncio
import sys
from dataclasses import dataclass

import aiohttp
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


@dataclass
class LoginCompany:
    user_id: int
    company_id: int


@dataclass
class LoginResponse:
    token: str
    companies: list[LoginCompany]


@dataclass
class Company:
    company_id: int
    company_name: str


@dataclass
class ReadyToShip:
    salesorder_id: int
    salesorder_no: str
    shipper: str


class Worker(QThread):
    success = Signal()
    finished = Signal()
    error = Signal(str, int)

    def __init__(self, email: str, password: str, company_names: list[str]):
        super().__init__()
        self.email = email
        self.password = password
        self.company_names = company_names

    def run(self):
        asyncio.run(self._run())

    async def _run(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://open.jubelio.com/core-api/login",
                    json={"email": self.email, "password": self.password},
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                login_data = LoginResponse(
                    token=data["token"],
                    companies=[
                        LoginCompany(user_id=c["user_id"], company_id=c["company_id"])
                        for c in data["companies"]
                    ],
                )

                all_companies: list[Company] = []
                for lc in login_data.companies:
                    async with session.get(
                        f"https://open.jubelio.com/core-api/v2/companies/{lc.user_id}",
                        headers={"Authorization": login_data.token},
                        params={"page": 1, "pageSize": 200},
                    ) as resp:
                        resp.raise_for_status()
                        items = await resp.json()
                        all_companies.extend(
                            Company(
                                company_id=i["company_id"],
                                company_name=i["company_name"],
                            )
                            for i in items
                        )

                for name in self.company_names:
                    name = name.strip()
                    if not name:
                        continue
                    matched = next(
                        (c for c in all_companies if c.company_name == name), None
                    )
                    if not matched:
                        continue

                    async with session.post(
                        "https://open.jubelio.com/core-api/switch-company",
                        headers={"Authorization": login_data.token},
                        json={"companyId": matched.company_id},
                    ) as resp:
                        resp.raise_for_status()

                    orders = await self._fetch_orders(session, login_data.token)

                    if not orders:
                        continue

                    batch_size = 5
                    for i in range(0, len(orders), batch_size):
                        batch = orders[i : i + batch_size]
                        ids = [o.salesorder_id for o in batch]
                        async with session.post(
                            "https://open.jubelio.com/core-api/wms/shipments/instant-courier/",
                            headers={"Authorization": login_data.token},
                            json={"ids": ids, "employee_id": self.email},
                        ) as resp:
                            resp.raise_for_status()
                        await asyncio.sleep(2)

                self.success.emit()
        except aiohttp.ClientResponseError as e:
            self.error.emit(str(e.message), e.status)
        except Exception as e:
            self.error.emit(str(e), 0)
        self.finished.emit()

    async def _fetch_orders(
        self, session: aiohttp.ClientSession, token: str
    ) -> list[ReadyToShip]:
        result: list[ReadyToShip] = []
        page = 1
        total_count = None
        while True:
            async with session.get(
                "https://open.jubelio.com/core-api/wms/sales/v2/orders/ready-to-ship/",
                headers={"Authorization": token},
                params={
                    "q": "",
                    "page": page,
                    "page_size": 25,
                    "type_courier": 0,
                    "sort_by": "transaction_date",
                    "sort_direction": "DESC",
                },
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
            if total_count is None:
                total_count = data["totalCount"]
            result.extend(
                ReadyToShip(
                    salesorder_id=i["salesorder_id"],
                    salesorder_no=i["salesorder_no"],
                    shipper=i["shipper"],
                )
                for i in data["data"]
            )
            if len(result) >= total_count:
                break
            page += 1
            await asyncio.sleep(2)
        return result


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Instant Courier Processor")
        self.setMinimumSize(700, 400)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)

        # Single container holding everything
        container = QWidget()
        container.setObjectName("container")
        container.setStyleSheet(
            "#container { border: 1px solid #ccc; border-radius: 8px; }"
        )
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(12, 12, 12, 12)

        # --- Left side: credentials ---
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("Email"))
        self.email_input = QLineEdit()
        left_layout.addWidget(self.email_input)
        left_layout.addWidget(QLabel("Password"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        left_layout.addWidget(self.password_input)
        left_layout.addStretch()
        container_layout.addWidget(left, 1)

        # --- Right side: company list ---
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.company_input = QLineEdit()
        self.company_input.setPlaceholderText("Company name...")
        right_layout.addWidget(self.company_input)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_company)
        btn_row.addWidget(add_btn)
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self._remove_company)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()
        right_layout.addLayout(btn_row)

        self.company_list = QListWidget()
        right_layout.addWidget(self.company_list, 1)
        container_layout.addWidget(right, 2)

        layout.addWidget(container, 1)

        # --- Run button ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.run_btn = QPushButton("Run")
        self.run_btn.setFixedWidth(80)
        self.run_btn.clicked.connect(self._run)
        btn_layout.addWidget(self.run_btn)
        layout.addLayout(btn_layout)

        self._worker: Worker | None = None

    def _add_company(self):
        name = self.company_input.text().strip()
        if name:
            self.company_list.addItem(name)
            self.company_input.clear()

    def _remove_company(self):
        row = self.company_list.currentRow()
        if row < 0:
            return
        name = self.company_list.item(row).text()
        confirm = QMessageBox.question(
            self,
            "Remove",
            f"Remove '{name}'?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.company_list.takeItem(row)

    def _run(self):
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        if not email or not password:
            QMessageBox.warning(
                self, "Missing fields", "Please enter email and password."
            )
            return
        company_names = [
            self.company_list.item(i).text() for i in range(self.company_list.count())
        ]
        if not company_names:
            QMessageBox.warning(
                self,
                "No companies",
                "Add at least one company.",
            )
            return

        self.run_btn.setEnabled(False)
        self._worker = Worker(email, password, company_names)
        self._worker.success.connect(self._on_success)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_success(self):
        QMessageBox.information(self, "Done", "All success!")

    def _on_error(self, msg: str, code: int):
        QMessageBox.critical(
            self, "Error", f"There is an error with HTTP code {code}: {msg}"
        )

    def _on_finished(self):
        self.run_btn.setEnabled(True)
        self._worker = None


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
