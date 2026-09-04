import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    id: root
    visible: true
    width: 1280
    height: 800
    title: "Hall Pass Kiosk"
    visibility: ApplicationWindow.FullScreen
    color: "#f5f3ef"

    property string activeBlock: backend ? backend.activeBlock : "Block_1"
    property string activeProfile: backend ? backend.activeProfile : "Block_A_Schedule"
    property string stateMode: backend ? backend.stateMode : "IDLE"
    property string activeStudent: backend ? backend.activeStudent : ""
    property string activePassType: backend ? backend.activePassType : ""
    property int elapsedSeconds: backend ? backend.elapsedSeconds : 0
    property int thresholdSeconds: backend ? backend.thresholdSeconds : 420
    property bool alarmMuted: backend ? backend.alarmMuted : false
    property var queueModel: backend ? backend.queue : []
    property var roster: backend ? backend.roster : []
    property var passHistory: backend ? backend.passHistory : []

    // Full-screen overdue flash (red/yellow)
    Rectangle {
        id: flashOverlay
        anchors.fill: parent
        color: "#991b1b"
        opacity: 0
        visible: stateMode === "OVERTIME"
        z: 100
        SequentialAnimation on opacity {
            running: flashOverlay.visible
            loops: Animation.Infinite
            NumberAnimation { from: 0.0; to: 0.35; duration: 450; easing.type: Easing.InOutQuad }
            NumberAnimation { from: 0.35; to: 0.0; duration: 450; easing.type: Easing.InOutQuad }
        }
        SequentialAnimation on color {
            running: flashOverlay.visible
            loops: Animation.Infinite
            ColorAnimation { from: "#991b1b"; to: "#facc15"; duration: 450 }
            ColorAnimation { from: "#facc15"; to: "#991b1b"; duration: 450 }
        }
        // Ensure clicks pass through when flashing
        MouseArea { anchors.fill: parent; enabled: false }
    }

    // Keyboard shortcuts
    Shortcut { sequence: "Escape"; onActivated: root.toggleFullscreen() }
    Shortcut { sequence: "F11"; onActivated: root.toggleFullscreen() }
    Shortcut { sequence: "Ctrl+Q"; onActivated: root.tryQuit() }
    Shortcut { sequence: "Alt+F4"; onActivated: root.tryQuit() }

    function toggleFullscreen() {
        if (visibility === ApplicationWindow.FullScreen) visibility = ApplicationWindow.Windowed
        else visibility = ApplicationWindow.FullScreen
    }
    function tryQuit() {
        // If admin password set, require auth via backend; else quit
        if (typeof backend !== "undefined" && backend.requireQuitAuth) {
            adminDialog.mode = "quit"
            adminDialog.open()
        } else {
            Qt.quit()
        }
    }

    header: ToolBar {
        height: 64
        background: Rectangle { color: "#1e3a5f" }
        RowLayout {
            anchors.fill: parent
            anchors.margins: 8
            Label {
                text: "HALL PASS"
                font.family: "Libre Baskerville"
                font.pixelSize: 20
                font.bold: true
                color: "#f8f6f0"
                font.letterSpacing: 1
            }
            Label {
                text: " — " + activeProfile + " • " + activeBlock
                color: "#e2e8f0"
                font.family: "Source Sans Pro"
                font.pixelSize: 13
            }
            Item { Layout.fillWidth: true }
            Label {
                text: stateMode
                color: stateMode==="OVERTIME"?"#991b1b":"#14532d"
                font.family: "Source Sans Pro"
                font.pixelSize: 13
                font.bold: true
            }
            Button {
                text: "Admin"
                font.pixelSize: 16
                padding: 10
                onClicked: { adminDialog.mode="admin"; adminDialog.open() }
            }
        }
    }

    // Main content
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 16
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16

        // Left: Roster
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 8
            color: "#ffffff"
            border.color: "#d1d5db"
            border.width: 1
            clip: true
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12
                // Sticky header — opaque, on top, never overlapped by list — starts below, not behind
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: headerCol.implicitHeight + 16
                    color: "#ffffff"
                    z: 2
                    ColumnLayout {
                        id: headerCol
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 4
                        Label {
                            text: activeBlock !== "" ? "Roster — " + activeBlock : "No active block — outside scheduled times"
                            color: "#1e3a5f"
                            font.family: "Libre Baskerville"
                            font.pixelSize: 17
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Label {
                            text: "Tap name to choose pass type"
                            color: "#334155"
                            font.family: "Source Sans Pro"
                            font.pixelSize: 12
                            font.italic: true
                            Layout.fillWidth: true
                        }
                        // Pass type selector modal
                        PassTypeDialog { id: passDialog }
                        Rectangle { Layout.fillWidth: true; height: 1; color: "#e5e7eb"; Layout.topMargin: 8 }
                        Label {
                            visible: roster.length === 0
                            text: activeBlock === "" ? "No block scheduled for now\nRoster appears only during its time slot" : "No students in this block"
                            color: "#64748b"
                            font.family: "Source Sans Pro"
                            font.pixelSize: 13
                            font.italic: true
                            wrapMode: Text.WordWrap
                            horizontalAlignment: Text.AlignHCenter
                            Layout.fillWidth: true
                            Layout.topMargin: 16
                        }
                    }
                }
                // Divider handled above, list is clipped and never draws under header
                ListView {
                    id: rosterView
                    visible: roster.length > 0
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.topMargin: 12
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    model: roster
                    spacing: 10
                    delegate: Rectangle {
                        width: rosterView.width
                        height: 68
                        radius: 6
                        color: "#f8f9fa"
                        border.color: "#e5e7eb"
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: modelData
                            color: "#1e293b"
                            font.family: "Source Sans Pro"
                            font.pixelSize: 16
                            font.bold: true
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                passDialog.student = modelData
                                passDialog.open()
                            }
                        }
                    }
                }
            }
        }

        // Center: Active pass — expanded to fill box, Return button dominates
        Rectangle {
            Layout.preferredWidth: 480
            Layout.fillHeight: true
            radius: 8
            color: stateMode==="OVERTIME" ? "#fef2f2" : "#ffffff"
            border.color: stateMode==="OVERTIME" ? "#991b1b" : "#d1d5db"
            border.width: 1
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10
                Label {
                    text: stateMode==="IDLE" ? "IDLE" : (activePassType + " PASS")
                    color: "#1e3a5f"
                    font.family: "Libre Baskerville"
                    font.pixelSize: 16
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    Layout.fillWidth: true
                }
                Label {
                    text: activeStudent || "Select a student"
                    color: activeStudent?"#1e293b":"#64748b"
                    font.family: "Libre Baskerville"
                    font.pixelSize: 26
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    verticalAlignment: Text.AlignVCenter
                    wrapMode: Text.WordWrap
                }

                // Timer — larger to fill between name and button
                Label {
                    text: {
                        var m = Math.floor(elapsedSeconds/60)
                        var s = elapsedSeconds%60
                        return (m<10?"0"+m:m)+":"+(s<10?"0"+s:s) + " / " + Math.floor(thresholdSeconds/60)+":00"
                    }
                    color: stateMode==="OVERTIME"?"#991b1b":"#334155"
                    font.family: "Source Sans Pro"
                    font.pixelSize: 42
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    Layout.fillWidth: true
                    visible: stateMode!=="IDLE"
                }
                ProgressBar {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 10
                    value: thresholdSeconds>0 ? Math.min(1, elapsedSeconds/thresholdSeconds) : 0
                    visible: stateMode!=="IDLE"
                }
                Label {
                    text: stateMode==="OVERTIME" ? "OVERTIME — Return pass now" : ""
                    color: "#991b1b"
                    font.family: "Source Sans Pro"
                    font.pixelSize: 13
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    Layout.fillWidth: true
                    visible: stateMode==="OVERTIME"
                }

                Item { Layout.fillHeight: true; visible: stateMode==="IDLE" }

                Button {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: 110
                    Layout.minimumHeight: 96
                    text: "Return Pass"
                    font.family: "Source Sans Pro"
                    font.pixelSize: 22
                    font.bold: true
                    enabled: stateMode!=="IDLE"
                    background: Rectangle {
                        color: parent.enabled?"#1e3a5f":"#e5e7eb"
                        radius: 8
                        border.color: parent.enabled?"#1e3a5f":"#d1d5db"
                        border.width: 1
                    }
                    onClicked: backend.returnPass()
                }
                Button {
                    Layout.fillWidth: true
                    height: 48
                    text: alarmMuted ? "Alarm Muted" : "Mute Alarm"
                    font.family: "Source Sans Pro"
                    font.pixelSize: 14
                    visible: stateMode==="OVERTIME"
                    enabled: !alarmMuted
                    background: Rectangle {
                        color: "#ffffff"
                        radius: 6
                        border.color: "#991b1b"
                        border.width: 1
                    }
                    onClicked: backend.muteAlarm()
                }
            }
        }

        // Right: Queue
        Rectangle {
            Layout.preferredWidth: 360
            Layout.fillHeight: true
            radius: 8
            color: "#ffffff"
            border.color: "#d1d5db"
            border.width: 1
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                Label {
                    text: "Queue"
                    color: "#1e3a5f"
                    font.family: "Libre Baskerville"
                    font.pixelSize: 18
                    font.bold: true
                }
                ListView {
                    id: queueView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: queueModel
                    spacing: 8
                    delegate: Rectangle {
                        width: queueView.width
                        height: 60
                        radius: 6
                        color: "#f8f9fa"
                        border.color: "#e5e7eb"
                        border.width: 1
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 8
                            Label {
                                text: (index+1)+". "+modelData.name
                                color: "#1e293b"
                                font.family: "Source Sans Pro"
                                font.pixelSize: 15
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                            Label {
                                text: modelData.passType
                                color: "#334155"
                                font.family: "Source Sans Pro"
                                font.pixelSize: 11
                                font.italic: true
                            }
                            Button {
                                text: "✕"
                                Layout.preferredWidth: 32
                                Layout.preferredHeight: 32
                                background: Rectangle { color: "#ffffff"; radius: 4; border.color: "#fecaca"; border.width: 1 }
                                contentItem: Text { text: parent.text; color: "#991b1b"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.pixelSize: 14; font.bold: true }
                                onClicked: backend.cancelQueue(modelData.name)
                            }
                        }
                    }
                }
            }
        }
        }

        // Pass History — bento row across bottom
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 148
            radius: 8
            color: "#ffffff"
            border.color: "#d1d5db"
            border.width: 1
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Rectangle { color: "#1e3a5f"; radius: 4; Layout.preferredWidth: 4; Layout.preferredHeight: 16 }
                    Label { text: "Pass History"; color: "#1e3a5f"; font.family: "Libre Baskerville"; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }
                    Label { text: passHistory.length + " recent"; color: "#475569"; font.family: "Source Sans Pro"; font.pixelSize: 11 }
                    Button {
                        text: "↻"
                        Layout.preferredWidth: 32
                        Layout.preferredHeight: 28
                        background: Rectangle { color: "#f1f5f9"; radius: 4; border.color: "#d1d5db"; border.width: 1 }
                        contentItem: Text { text: parent.text; color: "#334155"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.pixelSize: 14 }
                        onClicked: backend.refreshHistory()
                    }
                }
                // Horizontal history strip
                ListView {
                    id: historyView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    orientation: ListView.Horizontal
                    spacing: 10
                    clip: true
                    model: passHistory
                    delegate: Rectangle {
                        width: 200
                        height: 92
                        radius: 6
                        color: modelData.overtime === "OVERTIME" ? "#fef2f2" : modelData.overtime === "CANCELLED" ? "#fef9c3" : "#f8f9fa"
                        border.color: modelData.overtime === "OVERTIME" ? "#fecaca" : modelData.overtime === "CANCELLED" ? "#fde68a" : "#e5e7eb"
                        border.width: 1
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 4
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6
                                Label { text: modelData.student; color: "#1e293b"; font.family: "Source Sans Pro"; font.pixelSize: 12; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                Rectangle {
                                    color: modelData.passType === "Water" ? "#0ea5e9" : "#14532d"
                                    radius: 4
                                    Layout.preferredWidth: 44
                                    Layout.preferredHeight: 16
                                    Label { anchors.centerIn: parent; text: modelData.passType; color: "white"; font.pixelSize: 9; font.bold: true }
                                }
                            }
                            Label { text: modelData.block + " • " + modelData.date; color: "#475569"; font.family: "Source Sans Pro"; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6
                                Label { text: modelData.timeOut + " → " + modelData.timeIn; color: "#334155"; font.family: "Source Sans Pro"; font.pixelSize: 11; Layout.fillWidth: true }
                                Rectangle {
                                    color: modelData.overtime === "OVERTIME" ? "#991b1b" : modelData.overtime === "CANCELLED" ? "#f59e0b" : "#e5e7eb"
                                    radius: 4
                                    Layout.preferredWidth: modelData.overtime === "OVERTIME" ? 62 : modelData.overtime === "CANCELLED" ? 72 : 68
                                    Layout.preferredHeight: 16
                                    Label { anchors.centerIn: parent; text: modelData.overtime === "OVERTIME" ? "OVERTIME" : modelData.overtime === "CANCELLED" ? "CANCELLED" : modelData.duration; color: modelData.overtime === "OVERTIME" || modelData.overtime === "CANCELLED" ? "white" : "#334155"; font.pixelSize: 9; font.bold: true }
                                }
                            }
                        }
                    }
                    // Empty state
                    Label {
                        anchors.centerIn: parent
                        visible: passHistory.length === 0
                        text: "No passes yet — history will appear here"
                        color: "#64748b"
                        font.family: "Source Sans Pro"
                        font.pixelSize: 12
                        font.italic: true
                    }
                }
            }
        }
    }

    // Dialogs
    QueueDialog { id: queueDialog }
    AdminPanel { id: adminDialog }

    // Pass type chooser dialog component
    // Defined inline for simplicity if external file missing
}
