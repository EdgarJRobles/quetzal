# quetzal_units.py
# ---------------------------------------------------------------------------
# Unit-system helpers for Quetzal.
#
# Preferences stored at:
#   User parameter:BaseApp/Preferences/Mod/Quetzal
#   NominalSizeSystem  int    0 = DN (metric)   1 = NPS (imperial)
#   LengthUnit         str    "mm" | "in" | ""  (blank = follow FreeCAD schema)
# ---------------------------------------------------------------------------

import FreeCAD
from PySide.QtGui  import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                            QLabel, QComboBox, QRadioButton, QButtonGroup)

translate = FreeCAD.Qt.translate

# ---- DN <-> NPS mapping (ASME B36.10 / ISO 6708) ---------------------------

_DN_TO_NPS = {
    'DN6':    '1/8',    'DN8':    '1/4',    'DN10':   '3/8',
    'DN15':   '1/2',    'DN20':   '3/4',    'DN25':   '1',
    'DN32':   '1-1/4',  'DN40':   '1-1/2',  'DN50':   '2',
    'DN65':   '2-1/2',  'DN80':   '3',      'DN90':   '3-1/2',
    'DN100':  '4',      'DN125':  '5',      'DN150':  '6',
    'DN200':  '8',      'DN250':  '10',     'DN300':  '12',
    'DN350':  '14',     'DN400':  '16',     'DN450':  '18',
    'DN500':  '20',     'DN550':  '22',     'DN600':  '24',
    'DN650':  '26',     'DN700':  '28',     'DN750':  '30',
    'DN800':  '32',     'DN850':  '34',     'DN900':  '36',
    'DN1000': '40',     'DN1050': '42',     'DN1200': '48',
}
_NPS_TO_DN = {v: k for k, v in _DN_TO_NPS.items()}

# FreeCAD unit schemas that are imperial (US customary / Imperial decimal /
# Building US / Imperial for CNC)
_IMPERIAL_SCHEMAS = {2, 3, 5, 7}

_PREF_PATH  = 'User parameter:BaseApp/Preferences/Mod/Quetzal'
_UNITS_PATH = 'User parameter:BaseApp/Preferences/Units'


def _pref():
    return FreeCAD.ParamGet(_PREF_PATH)


# ---- Preference accessors ---------------------------------------------------

def get_size_system():
    """0 = DN (metric), 1 = NPS (imperial)."""
    return _pref().GetInt('NominalSizeSystem', 0)


def set_size_system(value):
    _pref().SetInt('NominalSizeSystem', int(value))


def get_length_unit():
    """
    Return the unit string to use when displaying dimensions.
    If the stored preference is blank, auto-detect from FreeCAD's unit schema.
    """
    stored = _pref().GetString('LengthUnit', '')
    if stored:
        return stored
    try:
        schema = FreeCAD.ParamGet(_UNITS_PATH).GetInt('UserSchema', 0)
        return 'in' if schema in _IMPERIAL_SCHEMAS else 'mm'
    except Exception:
        return 'mm'


def set_length_unit(unit_str):
    """Pass '' to revert to automatic detection from FreeCAD schema."""
    _pref().SetString('LengthUnit', unit_str.strip())


# ---- Formatting helpers -----------------------------------------------------

def format_psize(dn_string, system=None):
    """
    Convert a CSV DN string (e.g. 'DN50') to the display form for the
    current (or supplied) size system.
      system=0 -> 'DN50'
      system=1 -> 'NPS 2'
    Unknown DN strings are returned unchanged.
    """
    if system is None:
        system = get_size_system()
    if system == 1:
        nps = _DN_TO_NPS.get(dn_string)
        if nps:
            return 'NPS ' + nps
    return dn_string


def format_dim(mm_string, unit=None):
    """
    Convert a bare-number mm string from a CSV (e.g. '60.32') to a
    display string in the current (or supplied) length unit.
    Returns e.g. '60.32 mm' or '2.375 in'.
    Strings that already carry a unit suffix are converted via pq().
    """
    if not mm_string or not mm_string.strip():
        return mm_string
    if unit is None:
        unit = get_length_unit()
    raw = mm_string.strip()
    try:
        # If it is a plain number assume mm (CSV convention)
        try:
            float(raw)
            qty_str = raw + ' mm'
        except ValueError:
            qty_str = raw          # already has a unit
        qty = FreeCAD.Units.parseQuantity(qty_str)
        val = float(qty.getValueAs(unit))
        fmt = '{:.4g}' if unit == 'in' else '{:.5g}'
        return (fmt + ' {}').format(val, unit)
    except Exception:
        return mm_string


def format_size_label(row, system=None, unit=None):
    """
    Build the QListWidget label for one CSV row dict using the given
    (or current preference) size system and length unit.
    """
    label = format_psize(row.get('PSize', ''), system)
    if 'OD' in row:
        label += '  ' + format_dim(row['OD'], unit)
        if 'thk' in row:
            label += ' x ' + format_dim(row['thk'], unit)
    return label


def psize_for_od(od_mm_string, pipe_dict_list):
    """
    Reverse-lookup: given a raw mm OD string (e.g. '60.32'), scan
    pipe_dict_list for a row whose 'OD' value is within 0.1 mm and
    return its 'PSize' string (e.g. 'DN50').  Returns '' if not found.
    Used to label OD2 entries in the reducer and branch entries in the tee.
    """
    try:
        target = float(od_mm_string.strip())
    except (ValueError, AttributeError):
        return ''
    for row in pipe_dict_list:
        try:
            if abs(float(row['OD']) - target) < 0.15:
                return row['PSize']
        except (KeyError, ValueError):
            continue
    return ''


def format_secondary_label(od_mm, thk_mm, pipe_dict_list, system=None, unit=None):
    """
    Build a display label for a secondary port size (OD2/thk2 in reductions,
    branch OD2/thk2 in tees).  Looks up the DN name from pipe_dict_list so
    the label reads e.g. 'DN50  60.32 mm x 3.91 mm' or 'NPS 2  2.375 in x 0.154 in'.
    Falls back gracefully to raw mm if no matching PSize is found.
    """
    psize = psize_for_od(od_mm, pipe_dict_list)
    label = format_psize(psize, system) if psize else ''
    od_part  = format_dim(od_mm,  unit)
    thk_part = format_dim(thk_mm, unit)
    if label:
        return label + '  ' + od_part + ' x ' + thk_part
    else:
        return od_part + ' x ' + thk_part


# ---- Preference page --------------------------------------------------------

class QuetzalPreferencePage(QWidget):
    """
    Shown under Edit > Preferences > Quetzal.
    FreeCAD calls loadSettings() on open and saveSettings() on OK.
    """

    # Icon shown in the preference category list (reuse workbench icon)
    from os.path import join, dirname, abspath
    try:
        _iconPath = join(dirname(abspath(__file__)), 'iconz', 'quetzal.svg')
    except Exception:
        _iconPath = ''

    def __init__(self, parent=None):
        super(QuetzalPreferencePage, self).__init__(parent)
        self.setWindowTitle(translate('QuetzalPrefs', 'Quetzal'))
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # -- Nominal size system ----------------------------------------------
        sizeGrp = QGroupBox(
            translate('QuetzalPrefs', 'Nominal Pipe Size Display'))
        sizeLayout = QVBoxLayout(sizeGrp)
        self._sizeBG   = QButtonGroup(self)
        self._radioDN  = QRadioButton(
            translate('QuetzalPrefs', 'DN  (metric, e.g. DN50)'))
        self._radioNPS = QRadioButton(
            translate('QuetzalPrefs', 'NPS  (imperial, e.g. NPS 2)'))
        self._sizeBG.addButton(self._radioDN,  0)
        self._sizeBG.addButton(self._radioNPS, 1)
        sizeLayout.addWidget(self._radioDN)
        sizeLayout.addWidget(self._radioNPS)
        layout.addWidget(sizeGrp)

        # -- Length display unit ----------------------------------------------
        unitGrp = QGroupBox(
            translate('QuetzalPrefs', 'Dimension Display Unit'))
        unitLayout = QVBoxLayout(unitGrp)
        unitLayout.addWidget(QLabel(translate('QuetzalPrefs',
            'Unit used to display OD, thickness, and other dimensions in '
            'the size lists on insertion forms.\n'
            'Leave blank to follow the FreeCAD unit schema automatically.')))
        unitRow = QHBoxLayout()
        unitRow.addWidget(QLabel(translate('QuetzalPrefs', 'Unit:')))
        self._unitCombo = QComboBox()
        self._unitCombo.setEditable(True)
        self._unitCombo.addItems(['', 'mm', 'in', 'cm', 'm'])
        unitRow.addWidget(self._unitCombo)
        unitRow.addWidget(QLabel(
            translate('QuetzalPrefs', '(blank = auto from FreeCAD schema)')))
        unitRow.addStretch()
        unitLayout.addLayout(unitRow)

        # Live preview label
        prevRow = QHBoxLayout()
        prevRow.addWidget(QLabel(translate('QuetzalPrefs', 'Preview:')))
        self._preview = QLabel('')
        self._preview.setStyleSheet('color: grey;')
        prevRow.addWidget(self._preview)
        prevRow.addStretch()
        unitLayout.addLayout(prevRow)
        layout.addWidget(unitGrp)
        layout.addStretch()

        self._radioDN.toggled.connect(self._updatePreview)
        self._radioNPS.toggled.connect(self._updatePreview)
        self._unitCombo.currentTextChanged.connect(self._updatePreview)

        self.loadSettings()

    def loadSettings(self):
        if get_size_system() == 1:
            self._radioNPS.setChecked(True)
        else:
            self._radioDN.setChecked(True)
        unit = _pref().GetString('LengthUnit', '')
        idx = self._unitCombo.findText(unit)
        self._unitCombo.setCurrentIndex(idx if idx >= 0 else 0)
        if idx < 0:
            self._unitCombo.setCurrentText(unit)
        self._updatePreview()

    def saveSettings(self):
        set_size_system(1 if self._radioNPS.isChecked() else 0)
        set_length_unit(self._unitCombo.currentText())

    def _updatePreview(self):
        sys  = 1 if self._radioNPS.isChecked() else 0
        unit = self._unitCombo.currentText().strip() or get_length_unit()
        sample = {'PSize': 'DN50', 'OD': '60.32', 'thk': '3.91'}
        self._preview.setText(format_size_label(sample, sys, unit))
