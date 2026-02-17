// Yantra4D wrapper — YAPP Box Base
// Override template variables, then include generator

pcbLength = 80;
pcbWidth = 50;
pcbThickness = 1.6;
standoffHeight = 3;
wallThickness = 2;
baseWallHeight = 25;
lidWallHeight = 15;
roundRadius = 3;
paddingFront = 2;
paddingBack = 2;
paddingLeft = 2;
paddingRight = 2;
render_mode = 0;
fn = 0;

// Tell YAPP to render base only
include <vendor/yapp/YAPPgenerator_v3.scad>

printBaseShell = true;
printLidShell = false;
printSwitchExtenders = false;
showSideBySide = false;

YAPPgenerate();
