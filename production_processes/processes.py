# %%
from steer_opencell_data.DataManager import DataManager
from steer_opencell_production import __version__
import datetime as dt
import json
import pandas as pd
# %%
import os
os.environ["OPENCELL_ENV"] = "development"
# %%
# material types

from steer_opencell_design.Components.Containers.Cylindrical import CylindricalEncapsulation
from steer_opencell_design.Components.Containers.Pouch import PouchEncapsulation
from steer_opencell_design.Components.Containers.Prismatic import PrismaticEncapsulation
from steer_opencell_design.Constructions.ElectrodeAssemblies.Tape import Tape
from steer_opencell_design.Materials.ActiveMaterials import AnodeMaterial, CathodeMaterial
from steer_opencell_design.Materials.Binders import Binder
from steer_opencell_design.Materials.ConductiveAdditives import ConductiveAdditive
from steer_opencell_production.Components.Cell import Cell
from steer_opencell_production.Components.Coil import AnodeCoil, CathodeCoil
from steer_opencell_production.Components.CurrentCollector import CurrentCollector
from steer_opencell_production.Components.ElectrodeAssembly import ElectrodeAssembly
from steer_opencell_production.Components.ElectrodeStack import AnodeStack, CathodeStack
from steer_opencell_production.Components.Separator import BottomSeparator, Separator, TopSeparator
from steer_opencell_production.Components.Slurry import Slurry
from steer_opencell_production.Components.Solvent import Solvent
# %%
# machine classes

from steer_opencell_production.Energy.Electricity import Electricity
from steer_opencell_production.Machines.Assembler import CylindricalAssembler, PouchAssembler, PrismaticAssembler
from steer_opencell_production.Machines.Calenderer import Calenderer
from steer_opencell_production.Machines.CellMachine import (
    AgingMachine,
    DegassingMachine,
    FormationMachine,
    PackagingMachine,
    PretreatmentMachine,
    Tester,
)
from steer_opencell_production.Machines.Coater import Coater
from steer_opencell_production.Machines.Dryer import Dryer
from steer_opencell_production.Machines.Machine import _Machine
from steer_opencell_production.Machines.Mixer import AnodeMixer, CathodeMixer
from steer_opencell_production.Machines.Puncher import Puncher
from steer_opencell_production.Machines.Slitter import Slitter
from steer_opencell_production.Machines.Stacker import PunchedStacker, ZFoldStacker
from steer_opencell_production.Machines.Winder import FlatWinder, Winder
from steer_opencell_production.Personnel.SkilledWorker import SkilledWorker
# %%
# processes

# A process is one step of a production chain. It has its own input types and
# output type. It holds no machine: the user selects a machine for it.
#
# form_factor and internal_construction name the cell that a process fits.
# They are set only where the types do not show the cell design: assembly,
# winding and stacking. The values are the cell properties of the same name.

WOUND_INPUTS = {AnodeCoil, CathodeCoil, TopSeparator, BottomSeparator}
STACKED_INPUTS = {AnodeStack, CathodeStack, Separator}

PROCESSES = [
    # process_id, process_name, input types, output type, form_factor, internal_construction
    ("anode_mixing", "Anode mixing", {AnodeMaterial, Binder, ConductiveAdditive, Solvent}, Slurry, None, None),
    ("cathode_mixing", "Cathode mixing", {CathodeMaterial, Binder, ConductiveAdditive, Solvent}, Slurry, None, None),
    ("anode_coating", "Anode coating", {Slurry, CurrentCollector}, AnodeCoil, None, None),
    ("anode_drying", "Anode drying", {AnodeCoil}, AnodeCoil, None, None),
    ("anode_calendering", "Anode calendering", {AnodeCoil}, AnodeCoil, None, None),
    ("anode_slitting", "Anode slitting", {AnodeCoil}, AnodeCoil, None, None),
    ("anode_punching", "Anode punching", {AnodeCoil}, AnodeStack, None, None),
    ("cathode_coating", "Cathode coating", {Slurry, CurrentCollector}, CathodeCoil, None, None),
    ("cathode_drying", "Cathode drying", {CathodeCoil}, CathodeCoil, None, None),
    ("cathode_calendering", "Cathode calendering", {CathodeCoil}, CathodeCoil, None, None),
    ("cathode_slitting", "Cathode slitting", {CathodeCoil}, CathodeCoil, None, None),
    ("cathode_punching", "Cathode punching", {CathodeCoil}, CathodeStack, None, None),
    ("winding", "Winding", WOUND_INPUTS, ElectrodeAssembly, None, "Wound Jelly Roll"),
    ("flat_winding", "Flat winding", WOUND_INPUTS, ElectrodeAssembly, None, "Flat Wound Jelly Roll"),
    ("zfold_stacking", "Z-fold stacking", STACKED_INPUTS, ElectrodeAssembly, None, "ZFold Stack"),
    ("punched_stacking", "Punched stacking", STACKED_INPUTS, ElectrodeAssembly, None, "Punched Stack"),
    ("cylindrical_assembly", "Cylindrical assembly", {ElectrodeAssembly, CylindricalEncapsulation, Tape}, Cell, "Cylindrical Cell", None),
    ("prismatic_assembly", "Prismatic assembly", {ElectrodeAssembly, PrismaticEncapsulation}, Cell, "Prismatic Cell", None),
    ("pouch_assembly", "Pouch assembly", {ElectrodeAssembly, PouchEncapsulation}, Cell, "Pouch Cell", None),
    ("pretreatment", "Pretreatment", {Cell}, Cell, None, None),
    ("formation", "Formation", {Cell}, Cell, None, None),
    ("aging", "Aging", {Cell}, Cell, None, None),
    ("degassing", "Degassing", {Cell}, Cell, None, None),
    ("testing", "Testing", {Cell}, Cell, None, None),
    ("packaging", "Packaging", {Cell}, Cell, None, None),
]
# %%
# machine values

# Every value is a dummy value. The processes that the production notebooks use
# take the notebook values. Drying and the finishing steps have no notebook
# values, so they take dummy().
#
# The units are: power in kW, investment in USD, footprint in m², downtime in
# minutes, and scrap rate in percent. The throughput unit is different for each
# machine class. For example, a coater gives coils per minute and a mixer gives
# kg per second.

ELECTRICITY = Electricity(price=0.15)

COMMON = dict(
    technical_service_life=10,
    footprint=120.0,
    downtime=5,
    downtime_frequency=24,
    maintenance_rate=3.0,
)


def values(throughput, scrap, investment, power, crew=0):
    """Return the values of one machine."""
    return dict(
        max_throughput=throughput,
        scrap_rate=scrap,
        investment=investment,
        energy={ELECTRICITY: power},            # power while the machine processes material
        base_power={ELECTRICITY: 0.1 * power},  # power while the machine is on and idle
        labour={SkilledWorker: crew} if crew else {},
    )


def dummy():
    """Return the values of a machine that has no notebook values."""
    return values(10, 1.0, 1_000_000, 50, crew=1)


def slotted(**slot_values):
    """Return the dummy values of a machine that calculates its own throughput.

    A dryer, a pretreatment machine, an aging machine and a formation machine
    calculate the throughput from their slots, so they take no max_throughput.
    """
    machine_values = dummy()
    del machine_values["max_throughput"]
    return {**machine_values, **slot_values}


# Dummy slot values. A dwell time and a rest time are in h.
DRYER_SLOTS = dict(slots=20, dwell_time=2.5)            # coils, 2 h to 3 h in a vacuum oven
PRETREATMENT_SLOTS = dict(slots=2_000, dwell_time=24.0)  # cells, wetting for one day
AGING_SLOTS = dict(slots=20_000, dwell_time=336.0)       # cells, two weeks (BatPaC: 1 to 2 weeks)
FORMATION_SLOTS = dict(slots=1_000, cycles=2, c_rate=0.1, channel_current=10.0, rest_time=2.0)
# %%
# machines

ANODE = {"coil_type": AnodeCoil}
CATHODE = {"coil_type": CathodeCoil}

MACHINES = [
    # machine name, process_id, machine class, role, values
    ("Dummy anode mixer", "anode_mixing", AnodeMixer, {}, values(0.4, 1.5, 1_500_000, 60, crew=1)),
    ("Dummy cathode mixer", "cathode_mixing", CathodeMixer, {}, values(0.4, 2.0, 1_500_000, 60, crew=1)),
    ("Dummy anode coater", "anode_coating", Coater, ANODE, values(1.2, 4.0, 6_000_000, 350, crew=3)),
    ("Dummy anode dryer", "anode_drying", Dryer, ANODE, slotted(**DRYER_SLOTS)),
    ("Dummy anode calenderer", "anode_calendering", Calenderer, ANODE, values(4, 0.5, 1_200_000, 40, crew=1)),
    ("Dummy anode slitter", "anode_slitting", Slitter, ANODE, values(5, 1.0, 800_000, 25, crew=1)),
    ("Dummy anode puncher", "anode_punching", Puncher, ANODE, values(6, 1.5, 1_500_000, 30, crew=1)),
    ("Dummy cathode coater", "cathode_coating", Coater, CATHODE, values(1.2, 3.5, 6_000_000, 350, crew=3)),
    ("Dummy cathode dryer", "cathode_drying", Dryer, CATHODE, slotted(**DRYER_SLOTS)),
    ("Dummy cathode calenderer", "cathode_calendering", Calenderer, CATHODE, values(4, 0.7, 1_200_000, 40, crew=1)),
    ("Dummy cathode slitter", "cathode_slitting", Slitter, CATHODE, values(5, 1.2, 800_000, 25, crew=1)),
    ("Dummy cathode puncher", "cathode_punching", Puncher, CATHODE, values(6, 2.5, 1_500_000, 30, crew=1)),
    ("Dummy winder", "winding", Winder, {}, values(18, 3.0, 3_000_000, 70, crew=2)),
    ("Dummy flat winder", "flat_winding", FlatWinder, {}, values(18, 3.0, 3_000_000, 70, crew=2)),
    ("Dummy Z-fold stacker", "zfold_stacking", ZFoldStacker, {}, values(2, 3.0, 5_000_000, 60, crew=1)),
    ("Dummy punched stacker", "punched_stacking", PunchedStacker, {}, values(2, 3.0, 5_000_000, 60, crew=1)),
    ("Dummy cylindrical assembler", "cylindrical_assembly", CylindricalAssembler, {}, values(30, 2.0, 4_000_000, 90, crew=2)),
    ("Dummy prismatic assembler, 30 cells/min", "prismatic_assembly", PrismaticAssembler, {}, values(30, 2.0, 4_000_000, 90, crew=2)),
    ("Dummy prismatic assembler, 10 cells/min", "prismatic_assembly", PrismaticAssembler, {}, values(10, 2.0, 4_000_000, 90, crew=2)),
    ("Dummy pouch assembler", "pouch_assembly", PouchAssembler, {}, values(10, 2.0, 4_000_000, 90, crew=2)),
    ("Dummy pretreatment machine", "pretreatment", PretreatmentMachine, {}, slotted(**PRETREATMENT_SLOTS)),
    ("Dummy formation machine", "formation", FormationMachine, {}, slotted(**FORMATION_SLOTS)),
    ("Dummy aging machine", "aging", AgingMachine, {}, slotted(**AGING_SLOTS)),
    ("Dummy degassing machine", "degassing", DegassingMachine, {}, dummy()),
    ("Dummy tester", "testing", Tester, {}, dummy()),
    ("Dummy packaging machine", "packaging", PackagingMachine, {}, dummy()),
]
# %%
# build the machines and check them against their processes

types_by_process = {row[0]: (row[2], row[3]) for row in PROCESSES}
machines = []
for name, process_id, machine_class, role, machine_values in MACHINES:
    machine = machine_class(name=name, **COMMON, **machine_values, **role)
    input_types, output_type = types_by_process[process_id]
    # A process node accepts only a machine with exactly its types (ProcessNode.replace).
    if set(machine.input_types) != input_types or machine.output_type is not output_type:
        raise ValueError(f"'{name}' does not have the types of the process '{process_id}'.")
    machines.append((process_id, machine))

without_machine = set(types_by_process) - {process_id for process_id, _ in machines}
if without_machine:
    raise ValueError(f"These processes have no machine: {sorted(without_machine)}")
# %%
def class_path(cls):
    """Return the class path in the format that steer-core stores for a class."""
    return f"{cls.__module__}.{cls.__name__}"


date_created = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# %%
db = DataManager()
# %%
db.get_table_names()
# %%
db.drop_table('processes')
db.drop_table('machines')
# %%
db.create_table(table_name='processes', columns={
    'process_id': 'TEXT',
    'process_name': 'TEXT',
    'input_types': 'TEXT',
    'output_type': 'TEXT',
    'form_factor': 'TEXT',
    'internal_construction': 'TEXT',
    'date_created': 'TEXT',
    'version': 'TEXT',
})

db.create_table(table_name='machines', columns={
    'name': 'TEXT',
    'process_id': 'TEXT',
    'kind': 'TEXT',
    'object': 'TEXT',
    'date_created': 'TEXT',
    'version': 'TEXT',
    'reference': 'TEXT',
})
# %%
db.insert_data(table_name='processes', data=pd.DataFrame({
    'process_id': [row[0] for row in PROCESSES],
    'process_name': [row[1] for row in PROCESSES],
    'input_types': [json.dumps(sorted(class_path(t) for t in row[2])) for row in PROCESSES],
    'output_type': [class_path(row[3]) for row in PROCESSES],
    'form_factor': [row[4] for row in PROCESSES],
    'internal_construction': [row[5] for row in PROCESSES],
    'date_created': [date_created for _ in PROCESSES],
    'version': [__version__ for _ in PROCESSES],
}))

db.insert_data(table_name='machines', data=pd.DataFrame({
    'name': [machine.name for _, machine in machines],
    'process_id': [process_id for process_id, _ in machines],
    'kind': [machine.kind for _, machine in machines],
    'object': [machine.serialize() for _, machine in machines],
    'date_created': [date_created for _ in machines],
    'version': [__version__ for _ in machines],
    'reference': ["Dummy values" for _ in machines],
}))
# %%
db.get_data('processes')
# %%
db.get_data('machines')
# %%
# load every machine back and compare it with the machine that was saved

saved = {machine.name: machine for _, machine in machines}
for _, row in db.get_data('machines').iterrows():
    loaded = _Machine.deserialize(row['object'])
    if loaded.to_config() != saved[row['name']].to_config():
        raise ValueError(f"'{row['name']}' does not load back with the same values.")
# %%
