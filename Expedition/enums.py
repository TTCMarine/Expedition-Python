from enum import Enum, auto, IntEnum


class SysVar(IntEnum):
    """Enumeration of system variables."""
    BoatLength = 0
    BowToGps = auto()
    BoatWidth = auto()
    GpsOffset = auto()
    AltInterval = auto()
    LogHz = auto()
    TwdPeriod = auto()
    AltTwa = auto()
    WhatIfSet = auto()
    WhatIfDrift = auto()
    WhatIfTwd = auto()
    WhatIfTws = auto()
    HoldTwd = auto()
    HoldTws = auto()
    HoldSet = auto()
    HoldDrift = auto()
    Spare0 = auto()
    AutoLegRange = auto()
    TimerRoll = auto()
    CurrentRotLimit = auto()
    StartDampWind = auto()
    StartDampCurrent = auto()
    ValNumPersistent = auto()
    StripChartWandLat0 = auto()
    StripChartWandLon0 = auto()
    StripChartWandLat1 = auto()
    StripChartWandLon1 = auto()
    StripChartWandLat2 = auto()
    StripChartWandLon2 = auto()
    StripChartWandLat3 = auto()
    StripChartWandLon3 = auto()
    StripChartWand0 = auto()
    StripChartWand1 = auto()
    StripChartWand2 = auto()
    StripChartWand3 = auto()
    LaserLat = auto()
    LaserLon = auto()
    PrevMarkLat = auto()
    PrevMarkLon = auto()
    LegRng = auto()
    LegBrgM = auto()
    LegBrgT = auto()
    StartTime = auto()
    StartRSTime = auto()
    StartRSDist = auto()
    StartRSAng = auto()
    StartRSLatL = auto()
    StartRSLonL = auto()
    StartRPTime = auto()
    StartRPDist = auto()
    StartRPAng = auto()
    StartRPLatL = auto()
    StartRPLonL = auto()
    StartLSTime = auto()
    StartLSDist = auto()
    StartLSAng = auto()
    StartLSLatL = auto()
    StartLSLonL = auto()
    StartLPTime = auto()
    StartLPDist = auto()
    StartLPAng = auto()
    StartLPLatL = auto()
    StartLPLonL = auto()
    StartStrbLatX = auto()
    StartStrbLonX = auto()
    StartPortLatX = auto()
    StartPortLonX = auto()
    StartReachLat = auto()
    StartReachLon = auto()
    AboveLine = auto()
    StartDistToPort = auto()
    StartDistToStrb = auto()
    CursorTime = auto()
    CursorTimeP = auto()
    CursorTimeS = auto()
    CursorPolarTime = auto()
    CursorBearing = auto()
    CursorRange = auto()
    GateLat = auto()
    GateLon = auto()
    BowLat = auto()
    BowLon = auto()
    SternLat = auto()
    SternLon = auto()
    PrevMarkBrg = auto()
    PrevMarkRng = auto()
    CalTwa = auto()
    CalTws = auto()
    CalBsp = auto()
    CalLeeway = auto()
    CalAccel = auto()
    CalRot = auto()
    TimeLogPlayer = auto()
    TimeTests = auto()
    TimeEvents = auto()
    AisAgeLimit = auto()
    TimeGpsYYMMDD = auto()
    GSpotLat = auto()
    GSpotLon = auto()
    XteLat = auto()
    XteLon = auto()
    RemoteLinePortLat = auto()
    RemoteLinePortLon = auto()
    RemoteLineStrbLat = auto()
    RemoteLineStrbLon = auto()
    TestStartTime = auto()
    NumSysChannels = auto()


class SysBooleanVar(Enum):
    """Enumeration of system boolean variables."""
    Spare0 = 0
    LocalTime = auto()
    ErrorLogging = auto()
    MagneticMode = auto()
    Fahrenheit = auto()
    Keypad = auto()
    FourWands = auto()
    XteStandard = auto()
    AutoLegBisector = auto()
    PortMode = auto()
    Spare1 = auto()
    Spare2 = auto()
    SimpleRibbon = auto()
    TrackLoad = auto()
    Spare3 = auto()
    StartEnds = auto()
    LaylineROT = auto()
    LaylineTimeBelowZero = auto()
    Touch = auto()
    Slave = auto()
    AutoLegRange = auto()
    LogBoats = auto()
    CalcLeeway = auto()
    CalcLeewayComponents = auto()
    CalcPitchRollRate = auto()
    CalcCurrent = auto()
    CalcTw = auto()
    CalcYawRate = auto()
    CalcTwd = auto()
    CalcTwHeel = auto()
    CalcUseSog = auto()
    CalcUseCog = auto()
    CalcUsePitchRollRates = auto()
    CalcAwaMastRotation = auto()
    NumPersistent = auto()
    Quit = auto()
    AltId = auto()
    UseInstAsTarg = auto()
    UpdateDerived = auto()
    StartTimeGPS = auto()
    StartTimeReaching = auto()
    StartTimePort = auto()
    StartTimeStarboard = auto()
    StartMagnify = auto()
    StartRoll = auto()
    StartDownwind = auto()
    MOB = auto()
    AISDangerousCPA = auto()
    HoldTwd = auto()
    HoldTws = auto()
    HoldSet = auto()
    HoldDrift = auto()
    LogPlayback = auto()
    UserFlag = auto()
    Day = auto()
    Gate = auto()
    ThreadMutex = auto()
    Max = auto()


class SysIntVar(Enum):
    """Enumeration of system integer variables."""
    Theme = 0
    Depth = auto()
    Speed = auto()
    Distance = auto()
    Start = auto()
    DampingFilter = auto()
    Gps = auto()
    GpsPort = auto()
    NumPersistent = auto()
    Palette = auto()
    CoresPhysical = auto()
    CoresLogical = auto()
    MarkRounding = auto()
    Max = auto()


class Var(IntEnum):
    """Enumeration of Expedition variables."""
    Utc = 0  # Microsoft DATE type,utc system time
    Bsp = auto()
    Awa = auto()
    Aws = auto()
    Twa = auto()
    Tws = auto()
    Twd = auto()
    RudderFwd = auto()
    DeltaTargBsp = auto()
    Course = auto()
    Lwy = auto()
    Set = auto()
    Drift = auto()
    Hdg = auto()
    AirTemp = auto()
    SeaTemp = auto()
    Baro = auto()
    Depth = auto()  # metres
    Roll = auto()
    Pitch = auto()
    Rudder = auto()
    Tab = auto()
    ForestayLoad = auto()
    DownhaulLoad = auto()
    MastAngle = auto()
    ForestayLen = auto()
    Mast = auto()
    StbdLoadCell = auto()
    PortLoadCell = auto()
    Rake = auto()
    Volts = auto()
    Vmg = auto()
    ROT = auto()
    LayDistOnStrb = auto()
    LayTimeOnStrb = auto()
    LayPortBear = auto()
    LayDistOnPort = auto()
    LayTimeOnPort = auto()
    LayStrbBear = auto()
    GpsQuality = auto()  # 0 Bad, 1 Autonomous, 2 Differential, 3 p-code, 4,5 Rtk, 6 dr, if change this, need to change CPort::NmeaAPB()
    GpsHDOP = auto()
    GpsPDOP = auto()
    GpsVDOP = auto()
    GpsNumber = auto()  # Number of satellites in active constellation
    GpsAge = auto()  # Age of differential data
    GpsAltitude = auto()  # antenna height
    GpsGeoidSeparation = auto()
    GpsMode = auto()  # 0 = 1D, 1 = 2D, 2 = 3D, 3 = Auto, 6 = error
    Lat = auto()  # if add GPS vars, extend CCore::IsGPSvar()
    Lon = auto()
    Cog = auto()
    Sog = auto()
    DiffRefStn = auto()
    TargTwaN = auto()
    TargBspN = auto()
    TargVmg = auto()
    TargRoll = auto()
    PolarBsp = auto()
    PolarBspPercent = auto()
    PolarRoll = auto()
    ErrorCode = auto()
    StrbRunner = auto()
    PortRunner = auto()
    PolarBspN = auto()
    PolarBspPercentN = auto()
    TargTwaLwy = auto()  # target twa without leeway
    VmgPercent = auto()
    Vang = auto()
    Traveller = auto()
    MainSheet = auto()
    PolVmcToMark = auto()  # vmc if headed at mark
    KeelAngle = auto()
    KeelHeight = auto()
    Board = auto()
    EngineOilPressure = auto()
    RPM1 = auto()
    RPM2 = auto()
    BoardP = auto()
    BoardS = auto()
    OppTrack = auto()
    DistFinish = auto()
    StartTimeToPort = auto()
    StartTimeToStrb = auto()
    LineSquareWind = auto()
    StartDistToLine = auto()
    StartRchTimeToLine = auto()  # time to reach into line
    StartRchDistToLine = auto()
    StartRchBspToLine = auto()
    MarkTime = auto()
    NextMarkTimeOnPort = auto()
    NextMarkTimeOnStrb = auto()
    Xte = auto()
    Vmc = auto()
    MagVar = auto()
    Gwd = auto()
    Gws = auto()
    LayDist = auto()  # distance to layline we are heading to
    LayTime = auto()  # time to layline
    LayBear = auto()  # bearing of that layline
    VmcPercent = auto()
    PolVmc = auto()
    OptVmc = auto()
    OptVmcHdg = auto()
    OptVmcTwa = auto()
    DeltaTargTwa = auto()
    MarkRng = auto()
    MarkBrg = auto()
    MarkGpsTime = auto()
    MarkTwa = auto()
    PredSet = auto()
    PredDrift = auto()
    NextMarkRng = auto()
    NextMarkBrg = auto()
    NextMarkTwa = auto()
    RadarRng = auto()
    RadarBrg = auto()
    StartDistBelowLineStern = auto()
    Alt0 = auto()  # alternating number channels must be consecutive
    Alt1 = auto()
    Alt2 = auto()
    Alt3 = auto()
    Alt4 = auto()
    Alt5 = auto()
    Alt6 = auto()
    Alt7 = auto()
    Alt8 = auto()
    Alt9 = auto()  # num = (ExAlt9 - ExAlt0 + 1) = (ExAltMax - ExAlt0 + 1)	# defined in CoreMem.h
    AltMax = Alt9  # alternating channels must be consecutive

    NextMarkPolTime = auto()

    StartLineBiasDeg = auto()
    StartLineBiasLen = auto()

    StartLayPortBear = auto()  # laylines for start line
    StartLayStrbBear = auto()

    NextMarkAwa = auto()
    NextMarkAws = auto()

    StartRSTime = auto()  # turning to right, ending up on starboard
    StartRPTime = auto()  # turning to right, ending up on port
    StartLSTime = auto()  # turning to left, ending up on starboard
    StartLPTime = auto()  # turning to left, ending up on port

    GpsDistToRaceNote = auto()
    GpsTimeToRaceNote = auto()

    LogBsp = auto()
    LogSog = auto()
    StartGpsTimeToLine = auto()
    StartGpsTimeToBurn = auto()
    TargTwaS = auto()  # Start
    TargBspS = auto()  # Start

    GpsTime = auto()

    TwdPlus90 = auto()  # Twd + 90
    TwdLess90 = auto()  # Twd - 90

    Shadow = auto()
    ShadowOppTack = auto()

    DownhaulLoad2 = auto()

    TackAngle = auto()
    TackAnglePolar = auto()

    TargAwa = auto()

    StartTimeBurnPortX = auto()  # offset for the start stbd layline to the pin
    StartTimeBurnStrbX = auto()  # time to burn when tack onto starboard end starboard layline and sail to 20s from line
    StartLayTimeP = auto()
    StartLayTimeS = auto()

    MarkSet = auto()
    MarkDrift = auto()

    MarkLat = auto()
    MarkLon = auto()
    StartPortEndLat = auto()  # ends of line
    StartPortEndLon = auto()
    StartStrbEndLat = auto()
    StartStrbEndLon = auto()

    GpsHPE = auto()
    Humidity = auto()
    LeadPort = auto()
    LeadStbd = auto()
    Backstay = auto()

    User0 = auto()  # user channels must be consecutive
    User1 = auto()
    User2 = auto()
    User3 = auto()
    User4 = auto()
    User5 = auto()
    User6 = auto()
    User7 = auto()
    User8 = auto()
    User9 = auto()
    User10 = auto()
    User11 = auto()
    User12 = auto()
    User13 = auto()
    User14 = auto()
    User15 = auto()
    User16 = auto()
    User17 = auto()
    User18 = auto()
    User19 = auto()
    User20 = auto()
    User21 = auto()
    User22 = auto()
    User23 = auto()
    User24 = auto()
    User25 = auto()
    User26 = auto()
    User27 = auto()
    User28 = auto()
    User29 = auto()
    User30 = auto()
    User31 = auto()  # num = (ExUser31 - ExUser0 + 1) = (ExUserMax - ExUser0 + 1)
    UserMax = User31  # user channels must be consecutive

    StartTimeToGun = auto()
    StartTimeToLine = auto()
    StartTimeToBurn = auto()
    StartDistBelowLine = auto()
    StartDistBelowLineGun = auto()

    GateTimeOnPort = auto()  # this is to the gate mark
    GateDistOnStrb = auto()
    GateTimeOnStrb = auto()
    GateDistOnPort = auto()

    GateSpotTimeOnStrb = auto()
    GateSpotTimeOnPort = auto()

    LayPortBearUp = auto()
    LayStrbBearUp = auto()
    LayPortBearDn = auto()
    LayStrbBearDn = auto()

    TideLayPortTimeOnPort = auto()
    TideLayPortTimeOnStbd = auto()
    TideLayStbdTimeOnPort = auto()
    TideLayStbdTimeOnStbd = auto()
    TideLayPortTime = auto()
    TideLayStbdTime = auto()

    MaxLayPortBear = auto()
    MinLayPortBear = auto()
    MaxLayStrbBear = auto()
    MinLayStrbBear = auto()

    TwdLayMark = auto()
    TwdLayMarkOpp = auto()  # lay on other board

    DeltaBspSog = auto()
    DeltaHdgCog = auto()

    LayPortRatio = auto()
    LayStrbRatio = auto()

    FourierTwd = auto()
    FourierTws = auto()

    TargTwa = auto()
    TargBsp = auto()

    NearestTide = auto()

    PolCustom0 = auto()  # these need to be in this order : see CCore::DerivedPolarNumbers()
    PolCustom1 = auto()
    PolCustom2 = auto()
    PolCustom3 = auto()
    PolCustom0PC = auto()
    PolCustom1PC = auto()
    PolCustom2PC = auto()
    PolCustom3PC = auto()
    PolCustom0Targ = auto()
    PolCustom1Targ = auto()
    PolCustom2Targ = auto()
    PolCustom3Targ = auto()

    WaveSigHeight = auto()  # XDR from Volvo wave sensor
    WaveSigPeriod = auto()
    WaveMaxHeight = auto()
    WaveMaxPeriod = auto()

    SysGpsTimeDelta = auto()  # difference between system clock time and GPS (better than ExUtc - ExGsTime), was ExSlam

    Heave = auto()

    Mwa = auto()
    Mws = auto()
    Boom = auto()

    TargBspPercent = auto()
    HeadingToSteer = auto()
    HeadingToSteerPol = auto()

    StartBspToPort = auto()
    StartBspToStrb = auto()
    StartBspOnPort = auto()
    StartBspOnStrb = auto()

    Twist = auto()

    SailNow = auto()
    SailMark = auto()
    SailNext = auto()

    TwdTwisted = auto()

    TackLossVMGSec = auto()
    TackLossVMGMetres = auto()

    TripLog = auto()
    DeltaMarkBrgCog = auto()  # delta of cog and bearing to mark

    PitchRate = auto()
    RollRate = auto()

    DeltaPolBsp = auto()
    DeltaTargRoll = auto()

    DeflectorP = auto()
    RudderP = auto()
    RudderS = auto()
    RudderToe = auto()
    BspTransverse = auto()
    ForestayInner = auto()
    GateTime = auto()  # this is to the gate mark

    ZeroAhead = auto()
    BrgFromBoat0 = auto()
    RngFromBoat0 = auto()

    DeflectorS = auto()
    Bobstay = auto()
    Outhaul = auto()

    D0port = auto()
    D0starboard = auto()
    D1port = auto()
    D1starbboard = auto()
    V0port = auto()
    V0starbboard = auto()
    V1port = auto()
    V1starbboard = auto()

    StartTimeToPortSimple = auto()
    StartTimeToStrbSimple = auto()

    TargTwd = auto()
    TargTwdDelta = auto()
    PolarTws = auto()
    PolarTwsDelta = auto()
    PolarTwsPC = auto()

    OppTrackCog = auto()

    StartTimeToPortPinch = auto()
    StartTimeToStrbPinch = auto()

    PredTwd = auto()
    PredTws = auto()
    PredMSLP = auto()

    NextMarkLat = auto()
    NextMarkLon = auto()

    BoomAngle = auto()
    Cunningham = auto()
    ForestayInnerHalyard = auto()
    JibFurl = auto()
    JibHalyard = auto()

    MastCant = auto()

    J1 = auto()
    J2 = auto()
    J3 = auto()
    J4 = auto()
    FoilP = auto()
    FoilS = auto()

    Reacher = auto()
    Blade = auto()
    Staysail = auto()
    Solent = auto()
    Tack = auto()
    TackP = auto()
    TackS = auto()
    DeflectorUpper = auto()
    DeflectorLower = auto()
    WinchP = auto()
    WinchS = auto()
    SpinnakerP = auto()  # halyard
    SpinnakerS = auto()  # halyard
    MainHalyard = auto()
    Mast2 = auto()

    DeltaPolarRoll = auto()

    LayPortBearMean = auto()
    LayStrbBearMean = auto()
    LayPortBearSD = auto()
    LayStrbBearSD = auto()

    StartTimeToPortBurn = auto()
    StartTimeToStrbBurn = auto()

    DepthAft = auto()  # metres

    StartBurnPC = auto()
    PolarBspS = auto()
    StartGunBspTargPC = auto()
    StartGunBspPolPC = auto()
    StartLineTimeSP = auto()

    DeltaCourseCog = auto()
    LayTimeGPS = auto()

    EngineTemp = auto()
    EngineOilTemp = auto()  # ExEngineOilPressure is above
    TransmissionOilTemp = auto()
    TransmissionOilPressure = auto()
    FuelLevel = auto()  # N2k instance 0

    Amps = auto()
    ChargeState = auto()

    GateRng = auto()
    GateBrg = auto()

    Twg = auto()
    Twdg = auto()
    DewPt = auto()

    ForestayPlusTackLoad = auto()

    Gradient = auto()
    TwsWithGradient = auto()

    RudderPitchP = auto()
    RudderPitchS = auto()

    TestTime = auto()  # time since test start

    GateSquareWind = auto()
    GateBiasLen = auto()

    WaterLevel = auto()  # N2k instance 0
    WaterLevel2 = auto()  # N2k instance 1
    FuelLevel2 = auto()

    CANLoad = auto()  # NMEA 2000 BUS load
    CANFastPacketErrors = auto()

    PolarBspPercentS = auto()
    TargBspPercentS = auto()

    NumChannels = auto()  # number of channels
