import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "kigojomo.mail-linear"
  property bool menuOpen: false
  property bool detailsOpen: false
  readonly property bool opened: menuOpen
  property var health: ({})
  readonly property color ink: root.bar ? root.bar.foreground : Color.foreground
  readonly property color muted: Qt.rgba(ink.r, ink.g, ink.b, 0.58)
  readonly property color surface: Qt.rgba(ink.r, ink.g, ink.b, 0.055)
  readonly property color accent: "#8ddbb9"
  readonly property color signal: attention ? "#efb96b" : !active ? muted : accent
  readonly property string face: "sans-serif"
  readonly property string helper: Quickshell.env("HOME") + "/.config/omarchy/plugins/kigojomo.mail-linear/status.py"
  readonly property bool active: health.bridge === "active"
  readonly property bool busy: health.lastSync === "Syncing"
  readonly property bool attention: health.lastSync === "Needs attention"
  readonly property bool unchanged: /no (?:linear )changes (?:were justified|needed|made|required)|nothing actionable changed/i.test(health.summary || "")
  function refresh() { if (!statusProcess.running) statusProcess.running = true }
  function open() { menuOpen = true; refresh() }
  function close() { menuOpen = false }
  function toggle() { if (menuOpen) close(); else open() }
  function control(action) {
    Quickshell.execDetached(["python3", helper, action])
    if (action === "sync") health = Object.assign({}, health, {queued: true})
    refreshDelay.restart()
  }
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight
  Component.onCompleted: refresh()
  Timer { interval: root.menuOpen ? 5000 : 60000; repeat: true; running: true; onTriggered: root.refresh() }
  Timer { id: refreshDelay; interval: 1200; onTriggered: root.refresh() }
  Process {
    id: statusProcess
    command: ["python3", root.helper, "status"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: { try { root.health = JSON.parse(text) } catch (error) { root.health = ({bridge: "unavailable"}) } }
    }
  }
  component Label: Text {
    color: root.ink
    font.family: root.face
    font.pixelSize: Style.space(14)
    textFormat: Text.PlainText
    elide: Text.ElideRight
  }
  component Action: Button {
    foreground: root.ink
    fontFamily: root.face
    fontSize: Style.space(14)
    focusable: true
    height: Style.space(42)
    radius: Style.space(10)
  }
  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.busy ? "󰑓" : root.attention ? "󰀪" : "󰄬"
    active: root.menuOpen
    tooltipText: "Work Bridge · " + (root.health.lastSync || "Checking")
    onPressed: function(mouseButton) { if (mouseButton === Qt.LeftButton) root.toggle() }
  }
  PopupCard {
    id: popup
    anchorItem: button
    bar: root.bar
    owner: menuOwner
    open: root.menuOpen
    contentWidth: popup.fittedContentWidth(Style.space(480))
    contentHeight: popup.fittedContentHeight(Style.space(root.detailsOpen ? 690 : 540))
    Flickable {
      id: scroll
      anchors.fill: parent
      contentWidth: width
      contentHeight: content.implicitHeight
      clip: true
      boundsBehavior: Flickable.StopAtBounds
      Column {
        id: content
        width: scroll.width
        spacing: Style.space(20)

        // One title, one small engine label. Operational state belongs below.
        Item {
          width: parent.width; height: Style.space(28)
          Label { text: "Work Bridge"; font.pixelSize: Style.space(21); font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter }
          Label { text: "Luna · xhigh"; color: root.muted; font.pixelSize: Style.space(12); anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter }
        }

        // The visual anchor: a single, immediately readable bridge state.
        Rectangle {
          width: parent.width; height: Style.space(116); radius: Style.space(16)
          color: Qt.rgba(root.signal.r, root.signal.g, root.signal.b, 0.10)
          border.color: Qt.rgba(root.signal.r, root.signal.g, root.signal.b, 0.20)
          Row {
            x: Style.space(20); anchors.verticalCenter: parent.verticalCenter; spacing: Style.space(16)
            Rectangle {
              width: Style.space(44); height: width; radius: width / 2
              color: Qt.rgba(root.signal.r, root.signal.g, root.signal.b, 0.14)
              Text {
                anchors.centerIn: parent
                text: root.busy || root.health.queued ? "󰑓" : root.attention ? "󰀪" : !root.active ? "󰏤" : "󰄬"
                color: root.signal; font.family: Style.font.family; font.pixelSize: Style.space(24)
                RotationAnimation on rotation { from: 0; to: 360; duration: 1800; loops: Animation.Infinite; running: root.busy }
              }
            }
            Column {
              width: content.width - Style.space(100); spacing: Style.space(7)
              Label {
                width: parent.width
                text: root.health.queued ? "Sync queued" : root.busy ? "Updating your board" : root.attention ? "Needs your attention" : !root.active ? "Bridge paused" : "Watching mail"
                font.pixelSize: Style.space(25); font.weight: Font.DemiBold
              }
              Label {
                width: parent.width; color: root.muted; font.pixelSize: Style.space(13)
                text: root.attention ? "Open diagnostics to see what failed" : !root.active ? "Resume to process new updates" : root.busy ? "Reviewing sources against Linear" : "Automatic updates · morning backup"
              }
            }
          }
        }

        // A source-to-board diagram, instead of four competing health cards.
        Row {
          width: parent.width; spacing: Style.space(8)
          Column {
            width: (parent.width - Style.space(40)) * 0.57; spacing: Style.space(7)
            Repeater {
              model: [
                {name: "Thunderbird", tag: root.health.mailCache ? "Mail" : "No cache", ok: root.health.mailCache},
                {name: "TickTick", tag: root.health.ticktick ? "Work only" : "Off", ok: root.health.ticktick}
              ]
              delegate: Rectangle {
                required property var modelData
                width: parent.width; height: Style.space(37); radius: Style.space(9); color: root.surface
                Rectangle { x: Style.space(12); anchors.verticalCenter: parent.verticalCenter; width: Style.space(6); height: width; radius: width / 2; color: modelData.ok ? root.accent : "#efb96b" }
                Label { x: Style.space(26); anchors.verticalCenter: parent.verticalCenter; text: modelData.name; font.weight: Font.Medium }
                Label { anchors.right: parent.right; anchors.rightMargin: Style.space(12); anchors.verticalCenter: parent.verticalCenter; text: modelData.tag; color: root.muted; font.pixelSize: Style.space(11) }
              }
            }
          }
          Label { width: Style.space(24); height: Style.space(81); verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignHCenter; text: "→"; font.pixelSize: Style.space(23); color: root.muted }
          Rectangle {
            width: (parent.width - Style.space(40)) * 0.43; height: Style.space(81); radius: Style.space(12)
            color: root.surface
            Column {
              anchors.centerIn: parent; spacing: Style.space(5)
              Label { anchors.horizontalCenter: parent.horizontalCenter; text: "Linear ↗"; font.pixelSize: Style.space(18); font.weight: Font.DemiBold }
              Label { anchors.horizontalCenter: parent.horizontalCenter; text: "Pending work"; color: root.muted; font.pixelSize: Style.space(12) }
            }
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.control("open") }
          }
        }

        Column {
          width: parent.width; spacing: Style.space(10)
          Item {
            width: parent.width; height: Style.space(16)
            Label { text: "LAST REVIEW"; color: root.muted; font.pixelSize: Style.space(11); font.letterSpacing: 1.2; font.weight: Font.DemiBold }
            Label { anchors.right: parent.right; text: root.health.lastSyncAt || "—"; color: root.muted; font.pixelSize: Style.space(12) }
          }
          Item {
            width: parent.width; height: Style.space(52)
            Column {
              width: parent.width - Style.space(100); spacing: Style.space(5)
              Label { width: parent.width; text: root.attention ? "Review interrupted" : !root.health.lastSyncAt ? "No review yet" : root.unchanged ? "No changes needed" : "Review complete"; font.pixelSize: Style.space(18); font.weight: Font.Medium }
              Label { width: parent.width; text: root.attention ? "Your board may be out of date" : !root.health.lastSyncAt ? "Run your first sync below" : root.unchanged ? "Nothing new to add to your board" : "See changes and follow-ups in the report"; color: root.muted; font.pixelSize: Style.space(12) }
            }
            Action { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; width: Style.space(86); text: "Report ↗"; background: root.surface; onClicked: root.control("result") }
          }
        }

        Row {
          width: parent.width; spacing: Style.space(10)
          Action {
            width: parent.width - Style.space(106)
            text: root.busy ? "Syncing…" : root.health.queued ? "Queued" : "Sync now"
            background: root.accent; foreground: "#10251d"
            enabled: !root.busy && !root.health.queued; opacity: enabled ? 1 : 0.5
            onClicked: root.control("sync")
          }
          Action { width: Style.space(96); text: root.active ? "Pause" : "Resume"; background: root.surface; onClicked: root.control(root.active ? "pause" : "resume") }
        }

        Rectangle { width: parent.width; height: 1; color: root.ink; opacity: 0.10 }
        Item {
          width: parent.width; height: Style.space(24)
          Label { anchors.verticalCenter: parent.verticalCenter; text: "Connections " + (root.detailsOpen ? "⌃" : "⌄"); color: root.muted; font.pixelSize: Style.space(13) }
          Label { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: "TickTick ↗"; color: root.muted; font.pixelSize: Style.space(13)
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.control("ticktick") }
          }
          MouseArea { width: parent.width * 0.65; height: parent.height; cursorShape: Qt.PointingHandCursor; onClicked: root.detailsOpen = !root.detailsOpen }
        }
        Column {
          width: parent.width; spacing: Style.space(10); visible: root.detailsOpen
          Repeater {
            model: [
              {name: "Thunderbird", value: root.health.mailCache ? root.health.cacheCount + " caches · " + (root.health.thunderbird ? "running" : "closed") : "Cache unavailable"},
              {name: "TickTick", value: root.health.ticktick ? "Work follow-ups · read only" : "Not configured"},
              {name: "Codex", value: root.health.codexLogin ? "Signed in" : "Sign-in required"},
              {name: "Linear", value: root.health.linear ? "Plugin enabled" : "Plugin unavailable"}
            ]
            delegate: Item {
              required property var modelData
              width: parent.width; height: Style.space(18)
              Label { text: modelData.name; color: root.muted; font.pixelSize: Style.space(12) }
              Label { anchors.right: parent.right; width: parent.width * 0.65; horizontalAlignment: Text.AlignRight; text: modelData.value; font.pixelSize: Style.space(12) }
            }
          }
          Label { width: parent.width; text: "TickTick: on mail events, manual sync & morning review."; color: root.muted; font.pixelSize: Style.space(11) }
          Action { width: parent.width; text: "Open diagnostics ↗"; background: root.surface; onClicked: root.control("diagnostics") }
        }
      }
      Rectangle { width: Style.space(3); radius: 2; height: Math.max(20, scroll.height * scroll.height / Math.max(1, scroll.contentHeight)); x: scroll.width - width; y: scroll.contentY / Math.max(1, scroll.contentHeight - scroll.height) * (scroll.height - height); visible: scroll.contentHeight > scroll.height; color: root.ink; opacity: 0.25 }
    }
  }
  QtObject { id: menuOwner; function close() { root.menuOpen = false } }
}
