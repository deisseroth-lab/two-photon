"""Class definining the file layout of the 2p raw and processed data."""


class Layout:
    def __init__(self, base_path, acquisition):
        self.base_path = base_path
        self.acquisition = acquisition
        self.prefix = acquisition.split("/")[-1]

    def path(self, stage, acquisition=None):
        return self.base_path / stage / (acquisition or self.acquisition)

    def backup_path(self, backup_path, stage):
        return backup_path / stage / self.acquisition

    def raw_xml_path(self):
        return self.path("raw") / f"{self.prefix}.xml"

    def raw_voltage_path(self):
        return self.path("raw") / f"{self.prefix}_Cycle00001_VoltageRecording_001.csv"
