import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "kigojomo.mail-linear"
  property bool menuOpen: false
  property var health: ({})
  readonly property string helper: Quickshell.env("HOME") + "/.config/omarchy/plugins/kigojomo.mail-linear/status.py"
  readonly property bool active: health.bridge === "active"
  readonly property bool ready: active && health.configured && health.codexLogin && health.thunderbird && health.mailCache && health.linear && health.inotify

  function refresh() {
    if (!statusProcess.running) statusProcess.running = true
  }
  function control(action) {
    Quickshell.execDetached(["python3", root.helper, action])
    refreshDelay.restart()
  }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  Component.onCompleted: refresh()
  Timer { interval: 60000; repeat: true; running: true; onTriggered: root.refresh() }
  Timer { id: refreshDelay; interval: 900; onTriggered: root.refresh() }

  Process {
    id: statusProcess
    command: ["python3", root.helper, "status"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        try { root.health = JSON.parse(text) } catch (error) { root.health = ({bridge: "unavailable"}) }
      }
    }
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: ""
    active: root.menuOpen
    tooltipText: "Mail to Linear: " + (root.health.lastSync === "Needs attention" ? "Last sync needs attention" : root.ready ? "Ready" : root.active ? "Check setup" : "Paused or unavailable")
    onPressed: function(mouseButton) {
      if (mouseButton === Qt.LeftButton) {
        root.menuOpen = !root.menuOpen
        if (root.menuOpen) root.refresh()
      }
    }
  }

  PopupCard {
    id: popup
    anchorItem: button
    bar: root.bar
    owner: menuOwner
    open: root.menuOpen
    contentWidth: popup.fittedContentWidth(Style.space(300))
    contentHeight: popup.fittedContentHeight(content.implicitHeight)

    Column {
      id: content
      anchors.fill: parent
      spacing: Style.space(8)

      Text {
        text: "Mail to Linear"
        color: root.bar ? root.bar.foreground : Color.foreground
        font.family: root.bar ? root.bar.fontFamily : Style.font.family
        font.pixelSize: Style.font.subtitle
        font.bold: true
      }
      Text {
        width: parent.width
        wrapMode: Text.WordWrap
        text: "Bridge: " + (root.health.bridge || "Checking")
            + "\nCodex: " + (root.health.codexLogin ? "signed in" : root.health.codex ? "sign in needed" : "missing")
            + "\nThunderbird: " + (root.health.thunderbird ? "running" : "closed")
            + "\nMail cache: " + (root.health.mailCache ? "ready" : "missing")
            + "\nProject setup: " + (root.health.configured ? "ready" : "needed")
            + "\nLinear: " + (root.health.linear ? "installed" : "missing")
            + "\nFile watcher: " + (root.health.inotify ? "ready" : "missing")
            + "\nLast run: " + (root.health.lastSync || "Checking")
            + (root.health.lastSyncAt ? " · " + root.health.lastSyncAt : "")
        color: root.bar ? root.bar.foreground : Color.foreground
        font.family: root.bar ? root.bar.fontFamily : Style.font.family
        font.pixelSize: Style.font.bodySmall
      }
      Button {
        width: parent.width
        text: root.active ? "Pause bridge" : "Resume bridge"
        focusable: true
        foreground: root.bar ? root.bar.foreground : Color.foreground
        onClicked: root.control(root.active ? "pause" : "resume")
      }
      Button {
        width: parent.width
        text: "Open Pending work"
        focusable: true
        foreground: root.bar ? root.bar.foreground : Color.foreground
        onClicked: root.control("open")
      }
      Button {
        width: parent.width
        text: "Refresh status"
        focusable: true
        foreground: root.bar ? root.bar.foreground : Color.foreground
        onClicked: root.refresh()
      }
    }
  }

  QtObject {
    id: menuOwner
    function close() { root.menuOpen = false }
  }
}
