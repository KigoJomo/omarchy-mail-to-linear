import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "kigojomo.mail-linear"
  property bool menuOpen: false
  readonly property bool opened: menuOpen
  property var health: ({})
  readonly property color ink: root.bar ? root.bar.foreground : Color.foreground
  readonly property string face: root.bar ? root.bar.fontFamily : Style.font.family
  readonly property string helper: Quickshell.env("HOME") + "/.config/omarchy/plugins/kigojomo.mail-linear/status.py"
  readonly property bool active: health.bridge === "active"
  readonly property bool busy: health.lastSync === "Syncing"
  readonly property bool attention: health.lastSync === "Needs attention"
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
  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.busy ? "󰑓" : "󰄬"
    active: root.menuOpen
    tooltipText: "Work Bridge · " + (root.health.lastSync || "Checking")
    onPressed: function(mouseButton) {
      if (mouseButton === Qt.LeftButton) { root.menuOpen = !root.menuOpen; if (root.menuOpen) root.refresh() }
    }
  }
  PopupCard {
    id: popup
    anchorItem: button
    bar: root.bar
    owner: menuOwner
    open: root.menuOpen
    contentWidth: popup.fittedContentWidth(Style.space(520))
    contentHeight: popup.fittedContentHeight(Style.space(680))
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
        spacing: Style.space(14)
        Row {
          width: parent.width
          spacing: Style.space(10)
          Rectangle {
            width: Style.space(42); height: width; radius: Style.space(12)
            color: Qt.rgba(root.ink.r, root.ink.g, root.ink.b, 0.09)
            Text { anchors.centerIn: parent; text: "󰄬"; color: root.ink; font.family: root.face; font.pixelSize: Style.space(22) }
          }
          Column {
            spacing: Style.space(3)
            Text { text: "Work Bridge"; color: root.ink; font.family: root.face; font.pixelSize: Style.space(22); font.bold: true }
            Text { text: "Thunderbird + TickTick → Linear"; color: Qt.rgba(root.ink.r, root.ink.g, root.ink.b, 0.65); font.family: root.face; font.pixelSize: Style.space(14) }
          }
        }
        Rectangle {
          width: parent.width; height: headline.implicitHeight + Style.space(24); radius: Style.space(12)
          color: root.attention ? "#503c29" : Qt.rgba(root.ink.r, root.ink.g, root.ink.b, 0.07)
          Column {
            id: headline
            x: Style.space(12); y: Style.space(12); width: parent.width - Style.space(24); spacing: Style.space(5)
            Text { text: root.health.queued ? "Sync queued" : root.busy ? "Updating your work board…" : !root.active ? "Bridge paused" : root.attention ? "Last run needs attention" : "Watching for new mail"; color: root.attention ? "#ffd8a8" : root.ink; font.family: root.face; font.pixelSize: Style.space(15); font.bold: true }
            Text { width: parent.width; wrapMode: Text.WordWrap; text: !root.active ? "Resume to process queued changes." : "TickTick is checked with mail-triggered runs, Sync now and morning reconciliation."; color: root.attention ? "#ffd8a8" : root.ink; opacity: 0.75; font.family: root.face; font.pixelSize: Style.space(14) }
          }
        }
        Grid {
          width: parent.width; columns: 2; spacing: Style.space(8)
          Repeater {
            model: [
              {title: "Thunderbird", detail: root.health.mailCache ? root.health.cacheCount + " local caches · " + (root.health.thunderbird ? "app running" : "app closed") : "No configured caches found", ok: root.health.mailCache},
              {title: "TickTick", detail: root.health.ticktick ? root.health.ticktickLists + " · source enabled" : "Source not configured", ok: root.health.ticktick},
              {title: "Codex", detail: root.health.codexLogin ? "Signed in · Luna / xhigh" : "Check CLI and sign-in", ok: root.health.codexLogin},
              {title: "Linear", detail: root.health.linear ? "Plugin enabled · Pending work" : "Check plugin setup", ok: root.health.linear}
            ]
            delegate: Rectangle {
              required property var modelData
              width: (content.width - Style.space(8)) / 2; height: Style.space(88); radius: Style.space(10)
              color: Qt.rgba(root.ink.r, root.ink.g, root.ink.b, 0.05)
              Column {
                anchors.fill: parent; anchors.margins: Style.space(12); spacing: Style.space(7)
                Row {
                  spacing: Style.space(7)
                  Rectangle { width: Style.space(7); height: width; radius: width / 2; color: modelData.ok ? "#83c99a" : "#e4b76b"; anchors.verticalCenter: parent.verticalCenter }
                  Text { text: modelData.title; color: root.ink; font.family: root.face; font.pixelSize: Style.space(15); font.bold: true }
                }
                Text { width: parent.width; text: modelData.detail; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight; color: root.ink; opacity: 0.65; font.family: root.face; font.pixelSize: Style.space(14) }
              }
            }
          }
        }
        Row {
          width: parent.width; spacing: Style.space(8)
          Button { width: (parent.width - Style.space(8)) / 2; selected: true; text: root.busy ? "Sync running…" : root.health.queued ? "Queued" : "Sync all now"; enabled: !root.busy && !root.health.queued; focusable: true; bordered: true; fontSize: Style.space(14); foreground: root.ink; onClicked: root.control("sync") }
          Button { width: (parent.width - Style.space(8)) / 2; text: root.active ? "Pause bridge" : "Resume bridge"; focusable: true; bordered: true; fontSize: Style.space(14); foreground: root.ink; onClicked: root.control(root.active ? "pause" : "resume") }
        }
        Row {
          width: parent.width; spacing: Style.space(8)
          Button { width: (parent.width - Style.space(8)) / 2; text: "Open Linear ↗"; focusable: true; bordered: true; fontSize: Style.space(14); foreground: root.ink; onClicked: root.control("open") }
          Button { width: (parent.width - Style.space(8)) / 2; text: "Open TickTick ↗"; focusable: true; bordered: true; fontSize: Style.space(14); foreground: root.ink; onClicked: root.control("ticktick") }
        }
        Column {
          width: parent.width; spacing: Style.space(6)
          Text { text: "LATEST RESULT" + (root.health.lastSyncAt ? " · " + root.health.lastSyncAt : ""); color: root.ink; opacity: 0.6; font.family: root.face; font.pixelSize: Style.space(14); font.bold: true }
          Text { width: parent.width; text: root.health.summary || "Waiting for the first result…"; textFormat: Text.PlainText; wrapMode: Text.Wrap; maximumLineCount: 7; elide: Text.ElideRight; color: root.ink; font.family: root.face; font.pixelSize: Style.space(14) }
        }
        Row {
          width: parent.width; spacing: Style.space(8)
          Button { width: (parent.width - Style.space(8)) / 2; text: "Full result"; focusable: true; bordered: true; fontSize: Style.space(14); foreground: root.ink; onClicked: root.control("result") }
          Button { width: (parent.width - Style.space(8)) / 2; text: "Diagnostics"; focusable: true; bordered: true; fontSize: Style.space(14); foreground: root.ink; onClicked: root.control("diagnostics") }
        }
        Text { width: parent.width; text: "Mail events + morning backup · no hourly AI polling\nTickTick is read only. You stay in control of email."; wrapMode: Text.WordWrap; color: root.ink; opacity: 0.5; font.family: root.face; font.pixelSize: Style.space(14) }
      }
      Rectangle { width: Style.space(3); radius: 2; height: Math.max(20, scroll.height * scroll.height / scroll.contentHeight); x: scroll.width - width; y: scroll.contentY / Math.max(1, scroll.contentHeight - scroll.height) * (scroll.height - height); visible: scroll.contentHeight > scroll.height; color: root.ink; opacity: 0.25 }
    }
  }
  QtObject { id: menuOwner; function close() { root.menuOpen = false } }
}
