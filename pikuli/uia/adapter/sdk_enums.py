# -*- coding: utf-8 -*-

"""
Enums below are got from Windows SDK 8.1.
"""


from .helper_types import ApiEnumAutoval, ApiEnumExplicit, Enums


#
# See `UIAutomationCoreApi.h`
#

AsyncContentLoadedState = ApiEnumAutoval('AsyncContentLoadedState',
[
    'Beginning',
    'Progress',
    'Completed'
])


AutomationIdentifierType = ApiEnumAutoval('AutomationIdentifierType',
[
    'Property',
    'Pattern',
    'Event',
    'ControlType',
    'TextAttribute'
])


class ConditionType(ApiEnumExplicit):
    TRUE = 0
    FALSE = 1
    Property = 2
    And = 3
    Or = 4
    Not = 5


EventArgsType = ApiEnumAutoval('EventArgsType',
[
    'Simple',
    'PropertyChanged',
    'StructureChanged',
    'AsyncContentLoaded',
    'WindowClosed',
    'TextEditTextChanged'
])


NormalizeState = ApiEnumAutoval('NormalizeState',
[
    'None',    # Don't normalize
    'View',    # Normalize against condition in UiaCacheRequest
    'Custom'   # Normalize against supplied condition
])


ProviderType = ApiEnumAutoval('ProviderType',
[
    'BaseHwnd',
    'Proxy',
    'NonClientArea'
])


#
# See `UIAutomationClient.h`
#

class TreeScope(ApiEnumExplicit):
    Element = 0x01
    Children = 0x02
    Descendants = 0x04
    Parent = 0x08
    Ancestors = 0x10
    Subtree = (Element | Children) | Descendants


class PropertyConditionFlags(ApiEnumExplicit):
    None_ = 0x00
    IgnoreCase = 0x01


class AutomationElementMode(ApiEnumExplicit):
    None_ = 0
    Full = 1


#
# See `UIAutomationCore.h`
#
class NavigateDirection(ApiEnumExplicit):
    Parent = 0
    NextSibling = 1
    PreviousSibling = 2
    FirstChild = 3
    LastChild = 4


class ProviderOptions(ApiEnumExplicit):
    """ TODO: ??? DEFINE_ENUM_FLAG_OPERATORS(ProviderOptions) """
    ClientSideProvider = 0x001
    ServerSideProvider = 0x002
    NonClientAreaProvider = 0x004
    OverrideProvider = 0x008
    ProviderOwnsSetFocus = 0x010
    UseComThreading = 0x020
    RefuseNonClientSupport = 0x040
    HasNativeIAccessible = 0x080
    UseClientCoordinates = 0x100


class StructureChangeType(ApiEnumExplicit):
    ChildAdded = 0
    ChildRemoved = 1
    ChildrenInvalidated = 2
    ChildrenBulkAdded = 3
    ChildrenBulkRemoved = 4
    ChildrenReordered = 5


class TextEditChangeType(ApiEnumExplicit):
    None_ = 0
    AutoCorrect = 1
    Composition = 2
    CompositionFinalized = 3


class OrientationType(ApiEnumExplicit):
    None_ = 0
    Horizontal = 1
    Vertical = 2


class DockPosition(ApiEnumExplicit):
    Top = 0
    Left = 1
    Bottom = 2
    Right = 3
    Fill = 4
    None_ = 5


class ExpandCollapseState(ApiEnumExplicit):
    Collapsed = 0
    Expanded = 1
    PartiallyExpanded = 2
    LeafNode = 3


class ScrollAmount(ApiEnumExplicit):
    LargeDecrement = 0
    SmallDecrement = 1
    NoAmount = 2
    LargeIncrement = 3
    SmallIncrement = 4


class RowOrColumnMajor(ApiEnumExplicit):
    RowMajor = 0
    ColumnMajor = 1
    Indeterminate = 2


class ToggleState(ApiEnumExplicit):
    Off = 0
    On = 1
    Indeterminate = 2


class WindowVisualState(ApiEnumExplicit):
    Normal = 0
    Maximized = 1
    Minimized = 2


class SynchronizedInputType(ApiEnumExplicit):
    """ TODO: ??? DEFINE_ENUM_FLAG_OPERATORS(SynchronizedInputType) """
    KeyUp = 0x1
    KeyDown = 0x2
    LeftMouseUp = 0x4
    LeftMouseDown = 0x8
    RightMouseUp = 0x10
    RightMouseDown = 0x20


class WindowInteractionState(ApiEnumExplicit):
    Running = 0
    Closing = 1
    ReadyForUserInteraction = 2
    BlockedByModalWindow = 3
    NotResponding = 4


class TextUnit(ApiEnumExplicit):
    Character = 0
    Format = 1
    Word = 2
    Line = 3
    Paragraph = 4
    Page = 5
    Document = 6


class TextPatternRangeEndpoint(ApiEnumExplicit):
    Start = 0
    End = 1


class SupportedTextSelection(ApiEnumExplicit):
    None_ = 0
    Single = 1
    Multiple = 2


class LiveSetting(ApiEnumExplicit):
    Off = 0
    Polite = 1
    Assertive = 2


class ActiveEnd(ApiEnumExplicit):
    None_ = 0
    Start = 1
    End = 2


class CaretPosition(ApiEnumExplicit):
    Unknown = 0
    EndOfLine = 1
    BeginningOfLine = 2


class CaretBidiMode(ApiEnumExplicit):
    LTR = 0
    RTL = 1


class ZoomUnit(ApiEnumExplicit):
    NoAmount = 0
    LargeDecrement = 1
    SmallDecrement = 2
    LargeIncrement = 3
    SmallIncrement = 4


class AnimationStyle(ApiEnumExplicit):
    None_ = 0
    LasVegasLights = 1
    BlinkingBackground = 2
    SparkleText = 3
    MarchingBlackAnts = 4
    MarchingRedAnts = 5
    Shimmer = 6
    Other = -1


class BulletStyle(ApiEnumExplicit):
    None_ = 0
    HollowRoundBullet = 1
    FilledRoundBullet = 2
    HollowSquareBullet = 3
    FilledSquareBullet = 4
    DashBullet = 5
    Other = -1


class CapStyle(ApiEnumExplicit):
    None_ = 0
    SmallCap = 1
    AllCap = 2
    AllPetiteCaps = 3
    PetiteCaps = 4
    Unicase = 5
    Titling = 6
    Other = -1


class FlowDirections(ApiEnumExplicit):
    Default = 0
    RightToLeft = 1
    BottomToTop = 2
    Vertical = 4


class HorizontalTextAlignment(ApiEnumExplicit):
    Left = 0
    Centered = 1
    Right = 2
    Justified = 3


class OutlineStyles(ApiEnumExplicit):
    None_ = 0
    Outline = 1
    Shadow = 2
    Engraved = 4
    Embossed = 8


class TextDecorationLineStyle(ApiEnumExplicit):
    None_ = 0
    Single = 1
    WordsOnly = 2
    Double = 3
    Dot = 4
    Dash = 5
    DashDot = 6
    DashDotDot = 7
    Wavy = 8
    ThickSingle = 9
    DoubleWavy = 11
    ThickWavy = 12
    LongDash = 13
    ThickDash = 14
    ThickDashDot = 15
    ThickDashDotDot = 16
    ThickDot = 17
    ThickLongDash = 18
    Other = -1


class UIAutomationType(ApiEnumExplicit):
    Int = 0x00001
    Bool = 0x00002
    String = 0x00003
    Double = 0x00004
    Point = 0x00005
    Rect = 0x00006
    Element = 0x00007
    Array = 0x10000
    Out = 0x20000
    IntArray = Int | Array
    BoolArray = Bool | Array
    StringArray = String | Array
    DoubleArray = Double | Array
    PointArray = Point | Array
    RectArray = Rect | Array
    ElementArray = Element | Array
    OutInt = Int | Out
    OutBool = Bool | Out
    OutString = String | Out
    OutDouble = Double | Out
    OutPoint = Point | Out
    OutRect = Rect | Out
    OutElement = Element | Out
    OutIntArray = (Int | Array) | Out
    OutBoolArray = (Bool | Array) | Out
    OutStringArray = (String | Array) | Out
    OutDoubleArray = (Double | Array) | Out
    OutPointArray = (Point | Array) | Out
    OutRectArray = (Rect | Array) | Out
    OutElementArray = (Element | Array) | Out


def _get_sdk_enums():
    return [v for v in globals().values() if Enums.is_enum(v)]
