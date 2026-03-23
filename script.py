import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import sqlite3
import json
import os
from threading import Thread
from datetime import datetime


class DataImporterApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Json data import")
        self.root.geometry("600x500")
        self.root.resizable(False, False)

        self.VALIDATION_RULES = {
            'ril100': {  #ds100 - not empty, max 5 digits
                'name': 'DS100',
                'not_empty': True,
                'max_length': 5,
                'type': 'string'
            },
            'locationName': {  # longName - max 40 digits
                'name': 'longName',
                'max_length': 40,
                'type': 'string',
                'not_empty': False,
            },
            'name16': { #shorName - max 16 digits
                'name': 'shortName',
                'not_empty': True,
                'max_length': 16,
                'type': 'string'
            },
            'nrRb': { #NLNr in range [0; 9]
                'name': 'NLNr',
                'min': 0,
                'max': 9,
                'type': 'integer',
                'not_empty': False
            },
            'streckenNummer': { #lineNr - not empty, in range [1000; 9999]
                'name': 'lineNr',
                'not_empty': True,
                'min': 1000,
                'max': 9999,
                'type': 'integer'
            },
            'lageKm': { #absPos (lageKm in meters) has max 3 digits before and max 3 digits after decimal point (NNN.NNN)
                'name': 'absPos (lageKm)',
                'type': 'float',
                'max_digits_before': 3,
                'max_digits_after': 3,
                'not_empty': False
            },
            'anzahlGleise': { #trackNr in range [0; 2]
                'name': 'trackNr',
                'min': 0,
                'max': 2,
                'type': 'integer',
                'not_empty': False
            },
            'wirkung': { #dir in range [1; 18]
                'name': 'dir',
                'min': 1,
                'max': 18,
                'type': 'integer',
                'not_empty': False
            },
            'trackDisc': {  # dir in range [0; 1]
                'name': 'trackDisc',
                'min': 0,
                'max': 1,
                'type': 'integer',
                'not_empty': False
            }
        }


        # variables
        self.db_file = tk.StringVar()
        self.json_file = tk.StringVar()
        self.log_text = None
        self.is_running = False

        style = ttk.Style()
        style.theme_use('clam')

        # Main Frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Header
        title_label = ttk.Label(main_frame, text="DB InfraGO JSON Data Import", font=("Helvetica", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=10)

        # Browse DB from the PC
        ttk.Label(main_frame, text="Database (.db):").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.db_file, width=40).grid(row=1, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=self.select_db).grid(row=1, column=2)

        # Browse JSON from the PC
        ttk.Label(main_frame, text="JSON file:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.json_file, width=40).grid(row=2, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=self.select_json).grid(row=2, column=2)

        # Data import buttons frame
        button_frame = ttk.LabelFrame(main_frame, text="Import Options", padding="10")
        button_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=15)

        # Button 1: Import into ocpDS100_DB
        ttk.Button(button_frame, text="Update ocpDS100_DB Table",
                   command=self.import_ocp_ds100).pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        # Button 2: Import into ocpSD
        ttk.Button(button_frame, text="Update ocpSD Table",
                   command=self.import_ocp_sd).pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        # Logs
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)

        self.log_text = tk.Text(log_frame, height=15, width=70, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text['yscrollcommand'] = scrollbar.set

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

    def select_db(self):
        # Choose DB file (.db)
        filename = filedialog.askopenfilename(
            title="Select Database File",
            filetypes=[("SQLite Database", "*.db")]
        )
        if filename:
            self.db_file.set(filename)
            self.log("Database selected: " + os.path.basename(filename))

    def select_json(self):
        # Choose JSON file
        filename = filedialog.askopenfilename(
            title="Select JSON File",
            filetypes = [("JSON Files", "*.json")]
        )
        if filename:
            self.json_file.set(filename)
            self.log("JSON file selected: " + os.path.basename(filename))

    def log(self, message):
        # Add log message
        self.log_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update()

    def validate_inputs(self):
        # Проверить что выбраны файлы
        if not self.db_file.get():
            messagebox.showerror("Error", "Please select a database file!")
            return False

        if not self.json_file.get():
            messagebox.showerror("Error", "Please select a JSON file!")
            return False

        return True

    def _safe_int(self, value):
        # Convert into a number, returns None if empty
        if value is None or value == '' or str(value).strip() == '':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _safe_str(self, value):
        # Convert into a string, returns None if empty
        if value is None or str(value).strip() == '':
            return None
        return str(value)

    def _safe_float(self, value):
        # Convert into a float, returns None if empty
        if value is None or value == '' or str(value).strip() == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


    def _validate_field(self, value, json_field_name, stelle_data=None):
        # Check the field by the validation rules and returns (is_valid, error_message)

        if json_field_name not in self.VALIDATION_RULES:
            return True, None

        rule = self.VALIDATION_RULES[json_field_name]
        field_display_name = rule.get('name', json_field_name)

        # Not empty?
        if value is None or str(value).strip() == '':
            if not rule.get('not_empty', False):
                # Field is not obligatory - NULL in DB
                return True, None
            else:
                # Field is obligatory - NULL in DB
                return False, f"{field_display_name} cannot be empty"

        # Max length for strings
        if rule.get('type') == 'string':
            str_value = str(value)

            if rule.get('max_length'):
                if len(str_value) > rule['max_length']:
                    return False, f"{field_display_name}='{str_value}' exceeds max length {rule['max_length']}"

            return True, None


        # Integers
        if rule.get('type') == 'integer':
            try:
                int_value = int(value)

                if 'min' in rule and int_value < rule['min']:
                    return False, f"{field_display_name}={int_value} is below minimum {rule['min']}"

                if 'max' in rule and int_value > rule['max']:
                    return False, f"{field_display_name}={int_value} exceeds maximum {rule['max']}"

                return True, None
            except (ValueError, TypeError):
                return False, f"{field_display_name}={value} is not a valid integer"

        # Float
        if rule.get('type') == 'float':
            try:
                str_value = str(value)
                float_value = float(value)

                # Number of digits before and after .
                if '.' in str_value:
                    before_dot, after_dot = str_value.split('.')
                    before_digits = len(before_dot.lstrip('-'))
                    after_digits = len(after_dot)
                else:
                    before_digits = len(str_value.lstrip('-'))
                    after_digits = 0

                max_before = rule.get('max_digits_before', 3)
                max_after = rule.get('max_digits_after', 3)


                if before_digits > max_before:
                    return False, f"{field_display_name}={value} has {before_digits} digits before decimal (max {max_before})"
                if after_digits > max_after:
                    return False, f"{field_display_name}={value} has {after_digits} digits after decimal (max {max_after})"

                return True, None
            except (ValueError, TypeError):
                return False, f"{field_display_name}={value} is not a valid float"

        return True, None

    def import_ocp_ds100(self):
        # Import into ocpDS100_DB table
        if not self.validate_inputs():
            return

        thread = Thread(target=self._import_ocp_ds100_thread)
        thread.start()

    def _import_ocp_ds100_thread(self):
        try:
            self.is_running = True
            self.status_var.set("Importing ocpDS100_DB...")
            self.log("=" * 60)
            self.log("Starting import to ocpDS100_DB...")

            # Connect to database
            self.log("Connecting to database...")
            db = sqlite3.connect(self.db_file.get())
            db.execute("PRAGMA busy_timeout = 10000")
            db.execute("PRAGMA foreign_keys = OFF")
            db.execute("PRAGMA synchronous = OFF")
            self.log("Connection successful")

            # Load JSON
            self.log("Reading JSON file...")
            with open(self.json_file.get(), 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.log("JSON loaded successfully")

            # Cleaning table
            self.log("Cleaning table ocpDS100_DB...")
            db.execute("DELETE FROM ocpDS100_DB")
            self.log("Table cleaned")

            # Import data
            self.log("Importing data...")
            cursor = db.cursor()

            total_records = 0
            skipped_records = 0

            # ID logic
            current_id = 0

            if 'Betriebsstellen' in data and data['Betriebsstellen']:

                for index, stelle in enumerate(data['Betriebsstellen']):

                    # Check the values for DS100, longName, shortName, and NLNr in order to validation rules
                    REQUIRED_FIELDS = {
                        'ril100': 'ril100',
                        # 'locationName': 'locationName',
                        'name16': 'name16',
                        # 'nrRb': 'nrRb'
                    }
                    skip_record = False
                    ds100 = None

                    for json_field, rule_key in REQUIRED_FIELDS.items():
                        valid, error = self._validate_field(stelle.get(json_field), rule_key, stelle)

                        if not valid:
                            skipped_records += 1
                            # msg = f"SKIPPED (line {index}): {error}" if json_field == 'ril100' else f"SKIPPED (DS100='{ds100}'): {error}"
                            # self.log(msg)
                            if json_field == 'ril100':
                                self.log(f"WARNING SKIPPED (line {index}): {error}")
                            else:
                                ds100 = stelle.get('ril100', '???')
                                self.log(f"WARNING SKIPPED (DS100='{ds100}'): {error}")
                            skip_record = True
                            break
                        if json_field == 'ril100': #if ril100 is valid
                            ds100 = stelle.get('ril100', '')

                    if skip_record:
                        continue

                    # Obligatory
                    # DS100 - ril100
                    ds100 = stelle.get('ril100', '')

                    # short_name - name16
                    short_name = stelle.get('name16', '')

                    # Not Obligatory
                    # name - name16
                    # long_name = stelle.get('locationName', '')
                    long_name = self._safe_str(stelle.get('locationName'))

                    # type - typ
                    # type_val = stelle.get('typ', '')
                    type_val = self._safe_str(stelle.get('typ'))

                    # status - 'Betrieb' - always
                    status = 'Betrieb'

                    # NLNr
                    # nl_nr = int(stelle.get('nrRb', 0))
                    nl_nr = self._safe_int(stelle.get('nrRb'))

                    # BstNr - NULL
                    bst_nr = None

                    # countryID - NULL
                    country_id = None

                    cursor.execute("""
                        INSERT INTO ocpDS100_DB (ID, DS100, longName, shortName, type, status, NLNr, BstNr, countryID)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (current_id, ds100, long_name, short_name, type_val, status, nl_nr, bst_nr, country_id))

                    current_id += 1
                    total_records += 1

                self.log(f"Total inserted rows: {total_records}")
                # self.log(f"Total skipped rows: {skipped_records}")

            # Commit
            self.log("Committing transaction...")
            db.commit()
            self.log("Transaction committed")
            db.close()

            self.log("Import completed successfully!")
            self.log("=" * 60)
            self.status_var.set("Ready - Import completed")
            messagebox.showinfo("Success", f"Imported {total_records} records to ocpDS100_DB successfully!")

        except Exception as e:
            self.log(f"Error: {str(e)}")
            self.status_var.set("Error")
            messagebox.showerror("Error", f"Import failed:\n{str(e)}")

        finally:
            self.is_running = False


    def import_ocp_sd(self):
        # Import into ocpSD table
        if not self.validate_inputs():
            return

        thread = Thread(target=self._import_ocp_sd_thread)
        thread.start()

    def _import_ocp_sd_thread(self):
        try:
            self.is_running = True
            self.status_var.set("Importing ocpSD...")
            self.log("=" * 60)
            self.log("Starting import to ocpSD...")

            # Connect to database
            self.log("Connecting to database...")
            db = sqlite3.connect(self.db_file.get())
            db.execute("PRAGMA busy_timeout = 10000")
            db.execute("PRAGMA foreign_keys = OFF")
            db.execute("PRAGMA synchronous = OFF")
            self.log("Connection successful")

            # Load JSON
            self.log("Reading JSON file...")
            with open(self.json_file.get(), 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.log("JSON loaded successfully")

            # Clean table
            self.log("Cleaning table ocpSD...")
            db.execute("DELETE FROM ocpSD")
            self.log("Table cleaned")

            # Import data
            self.log("Importing data...")
            cursor = db.cursor()

            total_records = 0
            skipped_records = 0

            # ID logic
            current_id = 0

            if 'Strecken' in data and data['Strecken']:

                for strecke_index, strecke in enumerate(data['Strecken']):

                    # line_nr = int(strecke.get('streckenNummer', 0))
                    # Validate lineNr first - Obligatory
                    line_nr = strecke.get('streckenNummer', '')
                    valid, error = self._validate_field(line_nr, 'streckenNummer', strecke)
                    if not valid:
                        if 'ZugeordneteBetriebsstelle' in strecke:
                            skipped_records += len(strecke['ZugeordneteBetriebsstelle'])
                            self.log(f"WARNING SKIPPED {len(strecke['ZugeordneteBetriebsstelle'])} stations: lineNr error: {error}")
                        continue

                    line_nr = int(line_nr)


                    # Iterate through all Stellen in Strecke
                    if 'ZugeordneteBetriebsstelle' in strecke and strecke['ZugeordneteBetriebsstelle']:
                        for station in strecke['ZugeordneteBetriebsstelle']:


                            # Check the values for DS100, longName, shortName, and NLNr in order to validation rules
                            REQUIRED_FIELDS = {
                                'ril100': 'ril100',
                                'name16': 'name16',
                                # 'lageKm': 'lageKm',
                                # 'anzahlGleise': 'anzahlGleise',
                                # 'wirkung': 'wirkung'
                            }
                            skip_record = False
                            ds100 = None

                            for json_field, rule_key in REQUIRED_FIELDS.items():
                                valid, error = self._validate_field(station.get(json_field), rule_key, station)

                                if not valid:
                                    skipped_records += 1
                                    # msg = f"SKIPPED (line {strecke_index}): {error}" if json_field == 'ril100' else f"SKIPPED (DS100='{ds100}'): {error}"
                                    # self.log(msg)
                                    if json_field == 'ril100':
                                        self.log(f"WARNING SKIPPED (line {strecke_index}): {error}")
                                    else:
                                        ds100 = station.get('ril100', '???')
                                        self.log(f"WARNING SKIPPED (DS100='{ds100}'): {error}")
                                    skip_record = True
                                    break
                                if json_field == 'ril100': #if ril100 is valid
                                    ds100 = station.get('ril100', '')

                            if skip_record:
                                continue

                            # Obligatory
                            # lineNr - streckeNummer
                            line_nr_val = line_nr

                            # DS100 - ril100
                            ds100 = station.get('ril100', '')

                            # name - name16
                            name = station.get('name16', '')

                            # Not Obligatory
                            # lage_km = float(station.get('lageKm', 0)) # absPos - lageKm in meters (km * 1000)
                            lage_km = self._safe_float(station.get('lageKm'))
                            abs_pos = int(lage_km * 1000) if lage_km else None

                            # type - typ
                            # type_val = station.get('typ', '')
                            type_val = self._safe_str(station.get('typ'))

                            # trackNr - anzahlGleise
                            # track_nr = station.get('anzahlGleise', '')
                            track_nr = self._safe_int(station.get('anzahlGleise'))

                            # dir - wirkung
                            # dir_val = int(station.get('wirkung', 0))
                            dir_val = self._safe_int(station.get('wirkung'))


                            # trackDisc = 1 if trackNr = 0, otherwise trackDisc = 0
                            # track_disc = int(track_nr == 0)
                            track_disc = 1 if track_nr == 0 else (0 if track_nr is not None else None)


                            cursor.execute("""
                                INSERT INTO ocpSD (ID, lineNr, DS100, name, absPos, type, trackNr, dir, trackDisc)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (current_id, line_nr_val, ds100, name, abs_pos, type_val, track_nr, dir_val, track_disc))

                            current_id += 1
                            total_records += 1

                self.log(f"Total inserted rows: {total_records}")
                # self.log(f"Total skipped rows: {skipped_records}")

            # Commit
            self.log("Committing transaction...")
            db.commit()
            self.log("Transaction committed")
            db.close()

            self.log("Import completed successfully!")
            self.log("=" * 60)
            self.status_var.set("Ready - Import completed")
            messagebox.showinfo("Success", f"Imported {total_records} records to ocpSD successfully!")

        except Exception as e:
            self.log(f"Error: {str(e)}")
            self.status_var.set("Error")
            messagebox.showerror("Error", f"Import failed:\n{str(e)}")

        finally:
            self.is_running = False


if __name__ == "__main__":
    root = tk.Tk()
    app = DataImporterApp(root)
    root.mainloop()