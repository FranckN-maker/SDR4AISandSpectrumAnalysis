from matplotlib import pyplot as plt
import matplotlib.animation as animation
import matplotlib
from rtlsdr import RtlSdr
from matplotlib.patches import Rectangle
import numpy
from crc import Calculator, Crc16, Configuration, Register
import pandas as pd
import colorama
from colorama import Fore, Style
from tabulate import tabulate
from IPython.display import display, HTML
import os
import subprocess
import time



matplotlib.use("TKAgg")

def CRCtest(Data2check):
             
    config = Configuration(
        width=16,
        polynomial=0x1021,
        init_value=0xFFFF,
        final_xor_value=0xFFFF,
        reverse_input=False,
        reverse_output=False,
    )

    reg = Register(config)

    expected = HexaCRCin  # 0x1B18
    data = [int(l) for l in Data2check]
    recData = numpy.asarray(data)
    reg.init()
    reg.update(bytearray(data))

    if not expected == reg.digest():
        print(
            f"{Fore.RED}Warning --> CRCCheck OK :{expected == reg.digest()}{Style.RESET_ALL}"
        )
        CRC = "Not OK"
    else:
        print(f"{Fore.GREEN}CRCCheck OK :{expected == reg.digest()}{Style.RESET_ALL}")
        CRC = "OK"

    return CRC

def CorrelateSequ(SeqToSearch, Data):
    Sum = len(SeqToSearch)
    OutVec = []
    for i in range(0, len(Data) - Sum):
        OutVec.append(
            sum(numpy.logical_not(numpy.logical_xor(SeqToSearch, Data[i : i + Sum])))
        )

    return OutVec


def BitStuffing(Datausf):
    SeqSearch = [1, 1, 1, 1, 1]
    Sum = len(SeqSearch)
    OutVecStf = []
    VecStuff = numpy.zeros(len(Datausf), dtype=bool)
    CurruptedData = False
    for i in range(0, len(Datausf) - Sum):
        if (sum(numpy.logical_and(SeqSearch, Datausf[i : i + Sum]))) == 5:
            if Datausf[i + 5] == 0:
                OutVecStf.append(i + 5)
                VecStuff[i + 5] = True
            else:
                CurruptedData = True
    return VecStuff, OutVecStf, CurruptedData


def Bool2int(BoolVal):
    Val2return = 0
    for i, a in enumerate(BoolVal):
        Val2return = Val2return + a * 2 ** (i)

    return Val2return


def LongBool2int(LboolVal):
    NbHexNum = int(len(LboolVal) / 4)
    BigHexTrame = numpy.chararray((1, NbHexNum), itemsize=5)
    StrArray = []
    StrArrayAllBytes = []
    for i in range(0, NbHexNum):
        LboolFlipedHexa = numpy.flip(LboolVal[i * 4 : i * 4 + 4])
        BigHexTrameint = Bool2int(LboolFlipedHexa)
        BigHexTrame[0][i] = hex(BigHexTrameint)
        StrArray.append(hex(BigHexTrameint))
    for val in range(0, len(StrArray), 2):
        StrArrayAllBytes.append(StrArray[val][:] + StrArray[val + 1][2])

    return BigHexTrame, StrArrayAllBytes


def LongBool2intBytes(LboolVal):
    HexTable = [
        "0",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "a",
        "b",
        "c",
        "d",
        "e",
        "f",
    ]
    NbHexNum = int(len(LboolVal) / 8)
    BigHexTrame = numpy.chararray((NbHexNum), itemsize=4)
    decArray = []
    StrArrayAllBytes = []  # numpy.zeros((NbHexNum))]
    for i in range(0, NbHexNum, 1):
        Data = LboolVal[i * 8 : i * 8 + 8]
        LboolFlipedHexa0 = Bool2int(numpy.flip(Data[0:4]))
        LboolFlipedHexa1 = Bool2int(numpy.flip(Data[4:8]))
        decArray.append(LboolFlipedHexa0 * 16 + LboolFlipedHexa1)
        if i == 0:
            Hex = (
                "0x" + str(HexTable[LboolFlipedHexa0]) + str(HexTable[LboolFlipedHexa1])
            )

        else:
            Hex = (
                Hex
                + "0x"
                + str(HexTable[LboolFlipedHexa0])
                + str(HexTable[LboolFlipedHexa1])
            )
    return decArray, Hex


def ByteFlipp(Seq):
    NbHexNum = int(len(Seq) / 8)
    ByteTable = numpy.empty_like(Seq)
    for i in range(0, len(Seq), 8):
        ByteTable[i : i + 8] = numpy.flip(Seq[i : i + 8])

    return ByteTable


def binary_to_string(bits):
    return "".join([chr(int(i, 2)) for i in bits])


def twos_comp(val, bits):
    """compute the 2's complement of int value val"""
    if (val & (1 << (bits - 1))) != 0:  # if sign bit is set e.g., 8bit: 128-255
        val = val - (1 << bits)  # compute negative value
    return val

def synchroStartPreamble(f):

    MaxVal = f.max()
    Fbinary = f > MaxVal * 0.8
    sequence1 = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0]
    sequence2 = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0]
    sequence3 = [0, 1, 1, 1, 1, 1, 1, 0]
    SequenceBool1 = numpy.bool_(sequence1)
    SequenceBool2 = numpy.bool_(sequence2)
    SequenceBool3 = numpy.bool_(sequence3)

    PreambleDetect0 = numpy.array(CorrelateSequ(SequenceBool1, ~Fbinary))
    PreambleDetect1 = numpy.array(CorrelateSequ(SequenceBool2, ~Fbinary))
    PreambleDetect3 = numpy.array(CorrelateSequ(SequenceBool3, ~Fbinary))
    
    PosArray0 = numpy.where(PreambleDetect0 == 24, True, False)
    PosArray1 = numpy.where(PreambleDetect1 == 24, True, False)
    PosArray3 = numpy.where(PreambleDetect3 == 8, True, False)
    NbDetectChA = sum(PosArray0)
    NbDetectChB = sum(PosArray1)

    detectStatus = NbDetectChA != 0 or NbDetectChB !=0    

    return detectStatus, Fbinary, PreambleDetect0, PreambleDetect1, PreambleDetect3, PosArray0, PosArray1,PosArray3


def StrucAISMess(Seq):
    if len(Seq) != 168:
        print(f"{Fore.RED}Length Of Code sequence is wrong{Style.RESET_ALL}")
    Datlong = str(Seq[57:85])
    Datlongstr = Datlong.replace("]", "").replace("[", "").replace(" ", "")
    Nbitslong = len(Datlongstr)
    Datlat = str(Seq[85:112])
    Datlatstr = Datlat.replace("]", "").replace("[", "").replace(" ", "")
    Nbitslat = len(Datlatstr)

    class AISMessage:
        MessageID = Bool2int(numpy.flip(numpy.array(Seq[0:6])))
        RepeatIndicator = Bool2int(numpy.flip(numpy.array(Seq[6:8])))
        MMSI = Bool2int(numpy.flip(numpy.array(Seq[8:38])))
        MID_country = int(str(MMSI)[0:3])
        CountryVessel = MidPanda.loc[MidPanda.MID == MID_country].Country.values
        if not CountryVessel:
            CountryVessel = ["No Country identified"]
        Unused = Bool2int(numpy.flip(numpy.array(Seq[38:46])))
        SpeedOGround = Bool2int(numpy.flip(numpy.array(Seq[46:56])))
        PosAccuracy = Bool2int(numpy.flip(numpy.array([Seq[56]])))
        Long = twos_comp(int(Datlongstr, 2), Nbitslong) / 600000
        Lat = twos_comp(int(Datlatstr, 2), Nbitslat) / 600000
        CourseOVerGround = Bool2int(numpy.flip(numpy.array(Seq[112:124])))
        TrueHead = Bool2int(numpy.flip(numpy.array(Seq[124:133])))
        TimeStamp = Bool2int(numpy.flip(numpy.array(Seq[133:139])))
        Unused2 = Bool2int(numpy.flip(numpy.array(Seq[139:141])))
        CS_unit = Bool2int(numpy.flip(numpy.array([Seq[141]])))
        DisplayingFlag = Bool2int(numpy.flip(numpy.array([Seq[142]])))
        DSCFlag = Bool2int(numpy.flip(numpy.array([Seq[143]])))
        BandFlag = Bool2int(numpy.flip(numpy.array([Seq[144]])))
        AcceptMess22 = Bool2int(numpy.flip(numpy.array([Seq[145]])))
        Assigned = Bool2int(numpy.flip(numpy.array([Seq[146]])))
        RAIM = Bool2int(numpy.flip(numpy.array([Seq[147]])))
        RadioState = Bool2int(numpy.flip(numpy.array(Seq[148:168])))

    return AISMessage  # MMSI, Long, Lat

start = time.time()
print(start)

#####################################################################################################################
#
#                       Lancement de GNURADIO
#
#####################################################################################################################
testDetect = False



while testDetect == False:
    process = subprocess.Popen(['/home/nivole/.pyenv/versions/mambaforge/bin/python' ,
                             '/home/nivole/Documents/34_Gnuradio_Python/ProjectSDR/ais_rxArg.py',
                             '/home/nivole/Documents/34_Gnuradio_Python/ProjectSDR/OutAIS_GMSKBitsTest_Auto'])

    print('Running in process', process.pid)
    
    try:
        print('Running in process', process.pid)
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        print('Timed out - killing', process.pid)
        process.kill()
   
    fileRecrodAIS = numpy.fromfile(
    open("/home/nivole/Documents/34_Gnuradio_Python/ProjectSDR/OutAIS_GMSKBitsTest_Auto"),
    dtype=numpy.float64,
    )
    testDetect, Fbool, PreambleDetect0, PreambleDetect1, PreambleDetect3,PosArrayStart0, PosArrayStart1, PosArrayStop3 = synchroStartPreamble(fileRecrodAIS)
    print(f"Canaux détecté voie A: {sum(PosArrayStart0==True)}")
    print(f"Canaux détecté voie B: {sum(PosArrayStart1==True)}")
    
    print(testDetect)

print("Done")
end = time.time()
print(end - start)

#####################################Le fichier GMSKBitsTest_Auto Exist normalement ##############################

# width=16 poly=0x1021 init=0xffff refin=false refout=false xorout=0xffff check=0xd64e residue=0x1d0f name="CRC-16/GENIBUS"



MidFilePath = "/home/nivole/Documents/27_SDR_AIS/MID_BD/"
MidPanda = pd.read_csv(MidFilePath + "MID.csv")

NbDetectChA = numpy.where(PosArrayStart0==1)[0]
NbDetectChB = numpy.where(PosArrayStart1==1)[0]
IndexFirstAis = NbDetectChA[0]
# Search index 2 following




PosArray3End = numpy.where(PreambleDetect3[IndexFirstAis::] == 8)
IndexEndAis = PosArray3End[0][1]  # on prend la valeur 2 de la corr (index 1) afin de ne pas compter le flag de départ #
AIS_Seq = ~Fbool[IndexFirstAis : IndexFirstAis + IndexEndAis + 8]
SeqPayload = AIS_Seq[24:-8]
fig, axs = plt.subplots(2, 1)

axs[0].plot(AIS_Seq)  # 8 bits pour avoir le flag de fin #

# Seq[0:25] = 0
axs[0].vlines(
    x=24,
    ymin=0,
    ymax=1.2,
    color="green",
    linestyles="dashed",
    linewidth=3,
    label="start",
)
axs[0].vlines(
    x=len(AIS_Seq) - 8,
    ymin=0,
    ymax=1.2,
    color="green",
    linestyles="dashed",
    linewidth=3,
    label="stop",
)
axs[0].set_title("AIS TDMA Frame - useful data between dash lines", fontsize=32)

axs[1].plot(SeqPayload)
axs[1].set_title("AIS - useful data", fontsize=32)
plt.show()

# Bit de stuffing --> annulation du bourrage binaire de bit stuffing #

VecToErase, BitToErrase, corruptedBool = BitStuffing(SeqPayload)
fig, axs = plt.subplots()
axs.plot(SeqPayload)
axs.plot(VecToErase)
axs.set_title("AIS TDMA Frame - bit stuffing (orange)", fontsize=32)
plt.show()

# destuffing --> suppression des bit de bourrage
SeqPayLoadDestuf = numpy.delete(SeqPayload, BitToErrase)

# CRC 16 Error Check --> 16 derniers bits du checksum
CRCin = numpy.flip(SeqPayLoadDestuf[-16:])
HexaCRCin = Bool2int(CRCin)


DataWthoutCRC = SeqPayLoadDestuf[0:-16].astype(int)
DataWthoutCRCHex_2, HexadecData = LongBool2intBytes(DataWthoutCRC)

CRC = CRCtest(DataWthoutCRC)

fig, axs = plt.subplots()
axs.plot(SeqPayLoadDestuf)
axs.plot(DataWthoutCRC)

######################################################################
#
#               Bit et Byte inversion
#
######################################################################

FlippedData = ByteFlipp(DataWthoutCRC)
print(DataWthoutCRC)
print(FlippedData)
AisMessCl = StrucAISMess(FlippedData)
data = pd.DataFrame(
    [
        [
            AisMessCl.MessageID,
            AisMessCl.MMSI,
            AisMessCl.CountryVessel[0],
            AisMessCl.Lat,
            AisMessCl.Long,
            CRC,
        ]
    ],
    columns=["Message Type", "MMSI", "Pays", "Lattitude", "Longitude", "CRC Status"],
)

print(tabulate(data, headers="keys", tablefmt="psql"))

data.to_html("temp.html")

data.to_csv("List_Of_detection.csv", sep=";")

end = time.time()
print(end - start)
