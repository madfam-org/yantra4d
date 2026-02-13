// Yantra4D wrapper — Rugged Box Gasket

// --- Box Dimensions ---
internalBoxWidthXMm = 100;
internalboxLengthYMm = 60;
internalBoxTopHeightZMm = 20;
internalboxBottomHeightZMm = 20;

// --- Wall & Chamfer ---
boxWallWidthMm = 3.0;
boxChamferRadiusMm = 4;

// --- Seal ---
boxSealType = 2;
gasketSlotWidth = 2.2;
gasketSlotDepth = 2.2;

// --- Rim ---
rimWidthMm = 2;
rimHeightMm = 3;

// --- Ribs ---
numSideSupportRibs = 2;
supportRibThickness = 2;
supportRibWidth = 4;

// --- Dividers ---
countainerWidthXSections = 1;
boxLengthYSections = 1;
numCountainerWidthXSectionsToSkip = 0;
numBoxLengthYSectionsToSkip = 0;

// --- Hinges ---
numberOfHinges = 2;
hingeTotalWidthMm = 25;
hingeRadiusMm = 4;
hingeCenterOffsetMm = 5;

// --- Latches ---
numberOfLatches = 2;
latchSupportTotalWidth = 25;
latchCenterOffsetMm = 5;
latchClipCutoutAngle = 25;
latchOpenerLengthMultiplier = 1.4;

// --- Feet ---
isFeetAdded = false;
feetwidthMm = 4;
feetLengthMm = 10;
boxGapMm = 1.5;

// --- Quality ---
BoxPolygonStyle = 2;

// --- Mode control ---
viewBoxClosed = false;
generateBoxBottom = false;
generateBoxTop = false;
generateLatches = false;
generateGasket = true;
generateGasketTestObjects = false;
generateFeetIfSetInSettings = false;
generateEmptyBottomBoxTPUInsert = false;
generateEmptyTopBoxTPUInsert = false;

render_mode = 0;

include <vendor/rugged-box/RuggedBoxV1.scad>
