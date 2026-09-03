import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs

Dialog {
    id: admin
    title: "Admin Control Panel"
    modal: true
    width: 1120
    height: 800
    anchors.centerIn: parent
    standardButtons: Dialog.NoButton
    property string mode: "admin"
    property string currentTab: "Schedules"
    property string pendingRosterBlock: ""
    onClosed: backend.logoutAdmin()
    onVisibleChanged: if (!visible) backend.logoutAdmin()

    background: Rectangle {
        color: "#f5f3ef"
        radius: 4
        border.color: "#d1d5db"
        border.width: 1
    }

    Rectangle {
        id: gate
        anchors.fill: parent
        color: "#f5f3ef"
        radius: 4
        border.color: "#d1d5db"
        border.width: 1
        visible: !backend.isAdminAuthenticated
        // First-run: Set new admin password (no hardcoded credential in repo)
        ColumnLayout {
            anchors.centerIn: parent
            width: 380
            spacing: 14
            visible: backend.isFirstRun
            Label {
                text: "Set Admin Password"
                color: "#1e3a5f"
                font.pixelSize: 20
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
            }
            Label {
                text: "First run — create your admin password (min 4 chars). Default for testing is ‘admin123’ if you keep the template, but you must set your own on this device."
                color: "#475569"
                font.pixelSize: 11
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
            }
            TextField {
                id: newPassField
                echoMode: TextInput.Password
                placeholderText: "New password"
                font.pixelSize: 16
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                color: "#1e293b"
                placeholderTextColor: "#64748b"
                background: Rectangle { color: "#ffffff"; border.color: "#d1d5db"; radius: 4 }
            }
            TextField {
                id: confirmPassField
                echoMode: TextInput.Password
                placeholderText: "Confirm password"
                font.pixelSize: 16
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                color: "#1e293b"
                placeholderTextColor: "#64748b"
                background: Rectangle { color: "#ffffff"; border.color: "#d1d5db"; radius: 4 }
            }
            Label { id: firstRunError; text: backend.passwordStatus; color: backend.passwordStatus === "Password set" ? "#14532d" : "#ef4444"; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true; visible: backend.passwordStatus !== "" }
            Button {
                text: "Set Password & Unlock"
                Layout.fillWidth: true
                Layout.preferredHeight: 48
                contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 14 }
                background: Rectangle { color: "#1e3a5f"; radius: 4 }
                onClicked: {
                    backend.setInitialPassword(newPassField.text, confirmPassField.text)
                    if (backend.isAdminAuthenticated) {
                        newPassField.text = ""; confirmPassField.text = ""
                    }
                }
            }
            Button {
                text: "Cancel"
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                onClicked: admin.close()
            }
        }
        // Normal: Enter existing admin password
        ColumnLayout {
            anchors.centerIn: parent
            width: 360
            spacing: 14
            visible: !backend.isFirstRun
            Label {
                text: "Enter Admin PIN"
                color: "#1e3a5f"
                font.pixelSize: 20
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
            }
            TextField {
                id: pinField
                echoMode: TextInput.Password
                placeholderText: "Password"
                font.pixelSize: 18
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                color: "#1e293b"
                placeholderTextColor: "#64748b"
                background: Rectangle { color: "#ffffff"; border.color: "#d1d5db"; radius: 4 }
            }
            Label { id: pinError; text: ""; color: "#ef4444"; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Button {
                text: "Unlock"
                Layout.fillWidth: true
                Layout.preferredHeight: 48
                contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 15 }
                background: Rectangle { color: "#14532d"; radius: 4 }
                onClicked: {
                    if (backend.verifyAdmin(pinField.text)) {
                        pinError.text = ""
                        pinField.text = ""
                    } else {
                        pinError.text = "Incorrect password"
                    }
                }
            }
            Button {
                text: "Cancel"
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                onClicked: admin.close()
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        visible: backend.isAdminAuthenticated
        spacing: 14

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 56
            radius: 4
            color: "#1e3a5f"
            border.color: "#1e3a5f"
            RowLayout {
                anchors.fill: parent
                anchors.margins: 6
                spacing: 8
                Repeater {
                    model: [
                        {key: "Schedules", label: "Schedules"},
                        {key: "Rosters", label: "Rosters"},
                        {key: "Photos", label: "Photos"},
                        {key: "Audio", label: "Audio / TTS"},
                        {key: "System", label: "Pass & System"}
                    ]
                    delegate: Button {
                        text: modelData.label
                        checkable: true
                        checked: admin.currentTab === modelData.key
                        Layout.fillHeight: true
                        Layout.preferredWidth: 108
                        background: Rectangle {
                            color: checked ? "#ffffff" : "transparent"
                            radius: 4
                        }
                        contentItem: Text {
                            text: parent.text
                            color: parent.checked ? "#1e3a5f" : "#e2e8f0"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: 13
                            font.bold: parent.checked
                            font.family: "Libre Baskerville"
                        }
                        onClicked: admin.currentTab = modelData.key
                    }
                }
                Item { Layout.fillWidth: true }
                Button {
                    text: "✕ Close"
                    Layout.fillHeight: true
                    Layout.preferredWidth: 100
                    background: Rectangle { color: "#334155"
                                    radius: 4 }
                    onClicked: admin.close()
                }
            }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ScrollBar.vertical.policy: ScrollBar.AsNeeded
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            contentWidth: availableWidth
            padding: 2
            ColumnLayout {
                width: parent.width
                spacing: 16

                // ================= SCHEDULES TAB =================
                ColumnLayout {
                    visible: admin.currentTab === "Schedules"
                    spacing: 16
                    Layout.fillWidth: true
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 150
                        radius: 4
                        color: "#ffffff"
                        border.color: "#d1d5db"
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12
                            RowLayout {
                                spacing: 8
                                Layout.fillWidth: true
                                Rectangle { color: "#1e3a5f"
                                    radius: 4
                                    Layout.preferredWidth: 4
                                    Layout.preferredHeight: 18 }
                                Label { text: "Schedule Management"
                                    color: "#1e3a5f"
                                    font.pixelSize: 15
                                    font.bold: true }
                                Label { text: "• Unlimited custom blocks"
                                    color: "#334155"
                                    font.pixelSize: 12 }
                                Item { Layout.fillWidth: true }
                            }
                            Label {
                                text: "Create any number of blocks, name them, set times, and tag as Everyday (daily) or A/B (alternating). Rosters are per-block and the active roster is chosen by the current time on this device."
                                color: "#475569"
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                                font.pixelSize: 12
                            }
                            RowLayout {
                                spacing: 10
                                Layout.fillWidth: true
                                Label {
                                    text: "Today is:"
                                    color: "#1e3a5f"
                                    font.bold: true
                                }
                                Rectangle {
                                    color: "#1e3a5f"
                                    radius: 4
                                    border.color: "#1e3a5f"
                                    Layout.preferredHeight: 32
                                    Layout.preferredWidth: 300
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 8
                                        spacing: 6
                                        Rectangle {
                                            color: backend.activeDayLetter === "A" ? "#14532d" : backend.activeDayLetter === "B" ? "#991b1b" : "#334155"
                                            radius: 4
                                            Layout.preferredWidth: 8
                                            Layout.preferredHeight: 8
                                        }
                                        Label {
                                            text: backend ? (backend.activeBlock !== "" ? backend.activeBlock + " • Day " + backend.activeDayLetter + (backend.activeDayLetter === "A" ? " (A)" : backend.activeDayLetter === "B" ? " (B)" : "") : "No active block • Day " + backend.activeDayLetter) : "..."
                                            color: "white"
                                            font.pixelSize: 12
                                            elide: Text.ElideRight
                                            Layout.fillWidth: true
                                        }
                                    }
                                }
                                Item { Layout.fillWidth: true }
                                Button {
                                    text: "Reload"
                                    Layout.preferredHeight: 38
                                    Layout.preferredWidth: 90
                                    onClicked: backend.reloadSchedules()
                                }
                                Button {
                                    text: "Reset to Defaults"
                                    Layout.preferredHeight: 38
                                    Layout.preferredWidth: 150
                                    onClicked: backend.resetSchedules()
                                }
                            }
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 210
                        radius: 4
                        color: "#ffffff"
                        border.color: "#d1d5db"
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12
                            Label { text: "Weekday → A/B Day"
                                    color: "#1e3a5f"
                                    font.bold: true
                                    font.pixelSize: 13
                                    Layout.fillWidth: true }
                            Label { text: "Choose which letter day each weekday is. Blocks tagged A only appear on A days, B on B days, Everyday on both."
                                    color: "#475569"
                                    font.pixelSize: 11
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true }
                            GridLayout {
                                columns: 2
                                columnSpacing: 24
                                rowSpacing: 10
                                Layout.fillWidth: true
                                Repeater {
                                    model: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                                    delegate: RowLayout {
                                        spacing: 10
                                        Layout.fillWidth: true
                                        Label { text: modelData
                                            color: "#1e293b"
                                    Layout.preferredWidth: 85
                                    font.pixelSize: 13 }
                                        ComboBox {
                                            model: ["A", "B", "Late Start", "Early Dismissal", "PowerHour"]
                                            currentIndex: Math.max(0, ["A", "B", "Late Start", "Early Dismissal", "PowerHour"].indexOf(backend.dayDefaults[modelData] || "A"))
                                            onActivated: backend.setDayDefault(modelData, currentText)
                                            Layout.preferredWidth: 170
                                            Layout.preferredHeight: 36
                                            Layout.fillWidth: true
                                            background: Rectangle { color: "#ffffff"; border.color: "#1e3a5f"; border.width: 1; radius: 4 }
                                            contentItem: Text { text: parent.displayText; color: "#1e293b"; verticalAlignment: Text.AlignVCenter; leftPadding: 12; font.pixelSize: 13 }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    // Add Block card
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 170
                        radius: 6
                        color: "#ffffff"
                        border.color: "#1e3a5f"
                        border.width: 2
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 10
                            RowLayout {
                                spacing: 8
                                Layout.fillWidth: true
                                Rectangle { color: "#1e3a5f"; radius: 4; Layout.preferredWidth: 4; Layout.preferredHeight: 16 }
                                Label { text: "Create New Block"
                                    color: "#1e3a5f"
                                    font.bold: true
                                    font.pixelSize: 15
                                    Layout.fillWidth: true }
                                Label { text: backend.blocks.length + " blocks"
                                    color: "#475569"
                                    font.pixelSize: 11 }
                            }
                            Label { text: "Name, times (HH:MM 24h), and schedule: Everyday = daily, A/B = alternating, plus Late Start / Early Dismissal / PowerHour."
                                    color: "#475569"
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                    font.pixelSize: 11 }
                            RowLayout {
                                spacing: 10
                                Layout.fillWidth: true
                                TextField { id: newName; placeholderText: "Block name (e.g., Period 1)"; color: "#1e293b"; placeholderTextColor: "#64748b"; background: Rectangle { color: "#ffffff"; border.color: "#d1d5db"; radius: 4 } Layout.preferredWidth: 200; Layout.preferredHeight: 38; font.pixelSize: 13 }
                                TextField { id: newStart; placeholderText: "Start 08:00"; text: "08:00"; color: "#1e293b"; placeholderTextColor: "#64748b"; background: Rectangle { color: "#ffffff"; border.color: "#d1d5db"; radius: 4 } Layout.preferredWidth: 110; Layout.preferredHeight: 38; font.pixelSize: 13 }
                                Label { text: "→"; color: "#475569"; font.pixelSize: 16 }
                                TextField { id: newEnd; placeholderText: "End 09:30"; text: "09:30"; color: "#1e293b"; placeholderTextColor: "#64748b"; background: Rectangle { color: "#ffffff"; border.color: "#d1d5db"; radius: 4 } Layout.preferredWidth: 110; Layout.preferredHeight: 38; font.pixelSize: 13 }
                                ComboBox { id: newDayType; model: ["Everyday", "A", "B", "Late Start", "Early Dismissal", "PowerHour"]; Layout.preferredWidth: 140; Layout.preferredHeight: 38; background: Rectangle { color: "#ffffff"; border.color: "#1e3a5f"; border.width: 1; radius: 4 } contentItem: Text { text: parent.displayText; color: "#1e293b"; verticalAlignment: Text.AlignVCenter; leftPadding: 10; font.pixelSize: 13 } }
                                Button {
                                    text: "Create Block"
                                    Layout.preferredHeight: 38
                                    Layout.preferredWidth: 120
                                    background: Rectangle { color: "#14532d"; radius: 4 }
                                    contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 13 }
                                    onClicked: {
                                        if (backend.addBlock(newName.text, newStart.text, newEnd.text, newDayType.currentText)) {
                                            newName.text = ""; newStart.text="08:00"; newEnd.text="09:30"
                                        }
                                    }
                                }
                            }
                            Label { text: backend.rosterImportStatus; color: backend.rosterImportStatus.indexOf("already exists")>=0 || backend.rosterImportStatus.indexOf("failed")>=0 ? "#991b1b" : "#14532d"; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 11; visible: backend.rosterImportStatus !== "" && admin.currentTab==="Schedules" }
                        }
                    }
                    // Dynamic blocks list — bento boxed header
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 44
                        radius: 4
                        color: "#ffffff"
                        border.color: "#d1d5db"
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 8
                            Rectangle { color: "#1e3a5f"; radius: 4; Layout.preferredWidth: 4; Layout.preferredHeight: 16 }
                            Label { text: "Blocks — Tap Save to update, Delete to remove"; color: "#1e3a5f"; font.bold: true; font.pixelSize: 13; Layout.fillWidth: true; elide: Text.ElideRight }
                            Label { text: backend.blocks.length + " total"; color: "#475569"; font.pixelSize: 11 }
                        }
                    }
                    ColumnLayout {
                        spacing: 16
                        Layout.fillWidth: true
                        Repeater {
                            model: backend.blocks
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 124
                                radius: 4
                                color: "#ffffff"
                                border.color: "#d1d5db"
                                property string origName: modelData.name
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 10
                                    // Row 1: Name owns its line — no horizontal squeeze
                                    TextField {
                                        id: editName
                                        text: modelData.name
                                        placeholderText: "Block name"
                                        color: "#1e293b"
                                        placeholderTextColor: "#64748b"
                                        background: Rectangle { color: "#ffffff"; border.color: "#d1d5db"; radius: 4 }
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 38
                                        font.pixelSize: 13
                                    }
                                    // Row 2: Times + day_type + actions — spaced, not crammed
                                    RowLayout {
                                        spacing: 10
                                        Layout.fillWidth: true
                                        TextField {
                                            id: editStart
                                            text: modelData.start
                                            placeholderText: "08:00"
                                            color: "#1e293b"
                                            placeholderTextColor: "#64748b"
                                            background: Rectangle { color: "#ffffff"; border.color: "#d1d5db"; radius: 4 }
                                            Layout.preferredWidth: 96
                                            Layout.preferredHeight: 38
                                            font.pixelSize: 13
                                        }
                                        Label { text: "→"; color: "#475569"; font.pixelSize: 16 }
                                        TextField {
                                            id: editEnd
                                            text: modelData.end
                                            placeholderText: "09:30"
                                            color: "#1e293b"
                                            placeholderTextColor: "#64748b"
                                            background: Rectangle { color: "#ffffff"; border.color: "#d1d5db"; radius: 4 }
                                            Layout.preferredWidth: 96
                                            Layout.preferredHeight: 38
                                            font.pixelSize: 13
                                        }
                                        ComboBox {
                                            id: editDay
                                            model: ["Everyday", "A", "B", "Late Start", "Early Dismissal", "PowerHour"]
                                            currentIndex: Math.max(0, ["Everyday", "A", "B", "Late Start", "Early Dismissal", "PowerHour"].indexOf(modelData.day_type || "Everyday"))
                                            Layout.preferredWidth: 140
                                            Layout.preferredHeight: 38
                                            background: Rectangle { color: "#ffffff"; border.color: "#1e3a5f"; border.width: 1; radius: 4 }
                                            contentItem: Text { text: parent.displayText; color: "#1e293b"; verticalAlignment: Text.AlignVCenter; leftPadding: 10; font.pixelSize: 13 }
                                        }
                                        Item { Layout.fillWidth: true }
                                        Button {
                                            text: "Save"
                                            Layout.preferredHeight: 38
                                            Layout.preferredWidth: 76
                                            Layout.minimumWidth: 76
                                            background: Rectangle { color: "#1e3a5f"; radius: 4 }
                                            contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 12 }
                                            onClicked: backend.updateBlock(origName, editName.text, editStart.text, editEnd.text, editDay.currentText)
                                        }
                                        Button {
                                        text: "Delete"
                                        Layout.preferredHeight: 38
                                        Layout.preferredWidth: 76
                                        Layout.minimumWidth: 76
                                        background: Rectangle { color: "#991b1b"; radius: 4 }
                                        contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 12 }
                                        onClicked: backend.deleteBlock(origName)
                                    }
                                }
                            }
                        }
                    }
                    }
                }

                // ================= ROSTERS TAB =================
                ColumnLayout {
                    visible: admin.currentTab === "Rosters"
                    spacing: 16
                    Layout.fillWidth: true
                    Rectangle {
                        Layout.fillWidth: true
                        radius: 4
                        color: "#ffffff"
                        border.color: "#d1d5db"
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 10
                            RowLayout {
                                spacing: 8
                                Layout.fillWidth: true
                                Rectangle { color: "#14532d"
                                    radius: 4
                                    Layout.preferredWidth: 4
                                    Layout.preferredHeight: 18 }
                                Label { text: "Rosters — Per Block"
                                    color: "#1e3a5f"
                                    font.pixelSize: 15
                                    font.bold: true }
                                Item { Layout.fillWidth: true }
                                Label { text: backend.blocks.length + " blocks"
                                    color: "#475569"
                                    font.pixelSize: 11 }
                            }
                            Label {
                                text: "Each block you create appears below. Type names comma-separated or import CSV. Roster shown on main screen is the active block’s roster based on current time + A/B day."
                                color: "#475569"
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                                font.pixelSize: 12
                            }
                            Label { text: backend ? backend.rosterImportStatus : ""
                                    color: backend.rosterImportStatus.indexOf("failed")>=0 ? "#991b1b" : "#14532d"
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                    font.pixelSize: 12
                                    visible: backend.rosterImportStatus !== "" }
                        }
                    }
                    ColumnLayout {
                        spacing: 16
                        Layout.fillWidth: true
                        Repeater {
                            model: backend.blocks
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 140
                                radius: 4
                                color: "#ffffff"
                                border.color: modelData.day_type === "A" ? "#1e3a5f" : modelData.day_type === "B" ? "#7f1d1d" : "#d1d5db"
                                border.width: 2
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 10
                                    // Row 1: Name full width, no horizontal squeeze
                                    Label { text: modelData.name
                                        color: "#1e3a5f"
                                        font.bold: true
                                        font.pixelSize: 14
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                        wrapMode: Text.NoWrap }
                                    // Row 2: High-contrast bento meta — fully inside card, no hang
                                    RowLayout {
                                        spacing: 10
                                        Layout.fillWidth: true
                                        Rectangle {
                                            color: modelData.day_type === "A" ? "#1e3a5f" : modelData.day_type === "B" ? "#7f1d1d" : "#1e293b"
                                            radius: 6
                                            border.color: modelData.day_type === "A" ? "#1e3a5f" : modelData.day_type === "B" ? "#991b1b" : "#334155"
                                            border.width: 1
                                            Layout.preferredWidth: 92
                                            Layout.preferredHeight: 22
                                            Label { anchors.centerIn: parent; text: modelData.day_type === "Everyday" ? "Everyday" : "Day " + modelData.day_type; color: "white"; font.pixelSize: 11; font.bold: true; elide: Text.ElideRight }
                                        }
                                        Rectangle {
                                            color: "#ffffff"
                                            radius: 6
                                            border.color: "#1e3a5f"
                                            border.width: 1
                                            Layout.preferredWidth: 136
                                            Layout.preferredHeight: 22
                                            Label { anchors.centerIn: parent; text: modelData.start + " → " + modelData.end; color: "#1e3a5f"; font.pixelSize: 11; font.bold: true }
                                        }
                                        Item { Layout.fillWidth: true }
                                        Rectangle {
                                            color: "#f1f5f9"
                                            radius: 4
                                            border.color: "#d1d5db"
                                            border.width: 1
                                            Layout.preferredWidth: 96
                                            Layout.preferredHeight: 22
                                            Label { anchors.centerIn: parent; text: (backend.flatRosters[modelData.name] ? backend.flatRosters[modelData.name].length : 0) + " students"; color: "#1e293b"; font.pixelSize: 11; font.bold: true; elide: Text.ElideRight }
                                        }
                                    }
                                    // Row 3: TextField full width — owns its line, no button overlap
                                    TextField {
                                        id: rosterField
                                        text: backend.flatRosters[modelData.name] ? backend.flatRosters[modelData.name].join(", ") : ""
                                        placeholderText: "Comma separated — e.g., Alex Johnson, Sam Rivera"
                                        color: "#1e293b"
                                        placeholderTextColor: "#64748b"
                                        background: Rectangle { color: "#ffffff"; border.color: "#d1d5db"; radius: 4 }
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 38
                                        font.pixelSize: 12
                                    }
                                    // Row 4: Buttons each take equal space, no fixed-width crunch
                                    RowLayout {
                                        spacing: 10
                                        Layout.fillWidth: true
                                        Button {
                                            text: "Save Roster"
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 36
                                            background: Rectangle { color: modelData.day_type === "B" ? "#991b1b" : "#1e3a5f"; radius: 4 }
                                            contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 12 }
                                            onClicked: backend.setRosterForBlock(modelData.name, rosterField.text)
                                        }
                                        Button {
                                            text: "Import CSV"
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 36
                                            background: Rectangle { color: "#334155"; radius: 4 }
                                            contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 12 }
                                            onClicked: { admin.pendingRosterBlock = modelData.name; rosterFileDialog.open() }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    FileDialog {
                        id: rosterFileDialog
                        title: "Select Roster CSV"
                        nameFilters: ["CSV files (*.csv)"]
                        onAccepted: {
                            backend.importRosterForBlock(selectedFile, admin.pendingRosterBlock)
                        }
                    }
                }

                // ================= PHOTOS TAB =================
                ColumnLayout {
                    visible: admin.currentTab === "Photos"
                    spacing: 16
                    Layout.fillWidth: true
                    Rectangle {
                        Layout.fillWidth: true
                        radius: 4
                        color: "#ffffff"
                        border.color: "#d1d5db"
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 10
                            RowLayout {
                                spacing: 8
                                Layout.fillWidth: true
                                Rectangle { color: "#1e3a5f"; radius: 4; Layout.preferredWidth: 4; Layout.preferredHeight: 18 }
                                Label { text: "Photo Audit — Weekly Auto-Delete"; color: "#1e3a5f"; font.bold: true; font.pixelSize: 15; Layout.fillWidth: true }
                                Label { text: "7 days"; color: "#475569"; font.pixelSize: 11 }
                            }
                            Label { text: "Silent photos on pass out/in. Stored in " + backend.photosFolder + ". Auto-deleted after 7 days (daily check on launch). Use Refresh to reload, Purge to delete immediately, or Reveal to open folder."; color: "#475569"; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            Label { text: backend.photosStatus; color: backend.photosStatus.indexOf("failed")>=0 ? "#991b1b" : "#14532d"; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 11; visible: backend.photosStatus !== "" }
                        }
                    }
                    GridLayout {
                        columns: 3
                        columnSpacing: 12
                        rowSpacing: 12
                        Layout.fillWidth: true
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 92
                            radius: 4
                            color: "#ffffff"
                            border.color: "#d1d5db"
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 6
                                Label { text: "Photos"; color: "#1e293b"; font.bold: true; font.pixelSize: 12; Layout.fillWidth: true }
                                Label { text: backend.photoStats.count + " files • " + backend.photoStats.totalSize; color: "#1e3a5f"; font.bold: true; font.pixelSize: 16; Layout.fillWidth: true }
                                Label { text: "Oldest: " + backend.photoStats.oldest + "  •  Newest: " + backend.photoStats.newest; color: "#475569"; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                Label { text: backend.photoStats.folder; color: "#64748b"; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideMiddle }
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 92
                            radius: 4
                            color: "#ffffff"
                            border.color: "#d1d5db"
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 8
                                Label { text: "Actions"; color: "#1e293b"; font.bold: true; font.pixelSize: 12; Layout.fillWidth: true }
                                RowLayout {
                                    spacing: 8
                                    Layout.fillWidth: true
                                    Button { text: "Refresh"; Layout.fillWidth: true; Layout.preferredHeight: 36; background: Rectangle { color: "#ffffff"; radius: 4; border.color: "#d1d5db"; border.width: 1 } contentItem: Text { text: parent.text; color: "#1e293b"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 12 } onClicked: backend.refreshPhotos() }
                                    Button { text: "Purge 7d"; Layout.fillWidth: true; Layout.preferredHeight: 36; background: Rectangle { color: "#991b1b"; radius: 4 } contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 11 } onClicked: backend.purgeOldPhotos(7) }
                                }
                                Button { text: "Reveal Folder"; Layout.fillWidth: true; Layout.preferredHeight: 32; background: Rectangle { color: "#1e3a5f"; radius: 4 } contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 11 } onClicked: backend.revealPhotosFolder() }
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 92
                            radius: 4
                            color: "#fef2f2"
                            border.color: "#fecaca"
                            border.width: 1
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 6
                                RowLayout {
                                    spacing: 6
                                    Layout.fillWidth: true
                                    Label { text: "Camera"; color: "#991b1b"; font.bold: true; font.pixelSize: 12; Layout.fillWidth: true }
                                    Label { text: "Test real capture"; color: "#7f1d1d"; font.pixelSize: 10 }
                                }
                                RowLayout {
                                    spacing: 8
                                    Layout.fillWidth: true
                                    Button {
                                        text: "Test Camera"
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 30
                                        background: Rectangle { color: "#1e3a5f"; radius: 4 }
                                        contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 11 }
                                        onClicked: { var p = backend.testCameraCapture(); if (p !== "") backend.refreshPhotos() }
                                    }
                                    Button {
                                        text: "Open Settings"
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 30
                                        background: Rectangle { color: "#ffffff"; radius: 4; border.color: "#fecaca"; border.width: 1 }
                                        contentItem: Text { text: parent.text; color: "#991b1b"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 11 }
                                        onClicked: backend.openCameraSettings()
                                    }
                                }
                                Label { text: "If ‘NO CAMERA’, allow Terminal → relaunch"; color: "#991b1b"; font.pixelSize: 9; Layout.fillWidth: true; wrapMode: Text.WordWrap; elide: Text.ElideRight }
                            }
                        }
                    }
                    // Photo grid — bento cards with thumbnails
                    GridLayout {
                        columns: 4
                        columnSpacing: 12
                        rowSpacing: 12
                        Layout.fillWidth: true
                        Repeater {
                            model: backend.photos
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 156
                                radius: 6
                                color: "#ffffff"
                                border.color: "#d1d5db"
                                clip: true
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 6
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 84
                                        radius: 4
                                        color: "#f8f9fa"
                                        border.color: "#e5e7eb"
                                        border.width: 1
                                        clip: true
                                        Image {
                                            anchors.fill: parent
                                            anchors.margins: 2
                                            source: modelData.url
                                            fillMode: Image.PreserveAspectCrop
                                            cache: false
                                            asynchronous: true
                                        }
                                        // Fallback label if image fails
                                        Label { anchors.centerIn: parent; visible: false; text: "No preview"; color: "#64748b"; font.pixelSize: 10 }
                                    }
                                    Label { text: modelData.file; color: "#1e293b"; font.bold: true; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideMiddle }
                                    Label { text: modelData.date + (modelData.student !== "" ? " • " + modelData.student : "") + (modelData.block !== "" ? " • " + modelData.block : ""); color: "#475569"; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideRight }
                                    RowLayout {
                                        spacing: 6
                                        Layout.fillWidth: true
                                        Label { text: modelData.passType !== "" ? modelData.passType : "—"; color: modelData.overtime === "OVERTIME" ? "#991b1b" : "#14532d"; font.pixelSize: 9; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                        Button {
                                            text: "Delete"
                                            Layout.preferredWidth: 56
                                            Layout.preferredHeight: 24
                                            background: Rectangle { color: "#ffffff"; radius: 4; border.color: "#fecaca"; border.width: 1 }
                                            contentItem: Text { text: parent.text; color: "#991b1b"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.pixelSize: 10; font.bold: true }
                                            onClicked: backend.deletePhoto(modelData.path)
                                        }
                                    }
                                }
                            }
                        }
                    }
                    Label { visible: backend.photos.length === 0; text: "No photos yet — they appear after a pass is started/returned."; color: "#64748b"; font.italic: true; font.pixelSize: 12; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; Layout.topMargin: 16 }
                }

                // ================= AUDIO TAB =================
                ColumnLayout {
                    visible: admin.currentTab === "Audio"
                    spacing: 16
                    Layout.fillWidth: true
                    // Header bento
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 56
                        radius: 4
                        color: "#ffffff"
                        border.color: "#d1d5db"
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 8
                            Rectangle { color: "#1e3a5f"; radius: 4; Layout.preferredWidth: 4; Layout.preferredHeight: 18 }
                            Label { text: "Alarm & Voice"; color: "#1e3a5f"; font.bold: true; font.pixelSize: 15; Layout.fillWidth: true }
                            Label { text: "100% offline"; color: "#475569"; font.pixelSize: 11 }
                        }
                    }
                    // Bento grid — each setting is its own box, no nested Row crunch
                    GridLayout {
                        columns: 2
                        columnSpacing: 16
                        rowSpacing: 16
                        Layout.fillWidth: true
                        // Alarm Sound bento
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 168
                            radius: 4
                            color: "#ffffff"
                            border.color: "#d1d5db"
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 10
                                RowLayout {
                                    spacing: 8
                                    Layout.fillWidth: true
                                    Rectangle { color: "#1e3a5f"; radius: 4; Layout.preferredWidth: 4; Layout.preferredHeight: 14 }
                                    Label { text: "Alarm Sound"; color: "#1e293b"; font.bold: true; font.pixelSize: 13; Layout.fillWidth: true }
                                    Label { text: "Overtime alarm"; color: "#475569"; font.pixelSize: 11 }
                                }
                                Label { text: "Sound played when timer hits OVERTIME"; color: "#475569"; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                ComboBox { id: soundBox
                                    model: backend ? backend.alarmSounds : []; Component.onCompleted: if (backend) currentIndex = backend.alarmSounds.indexOf(backend.selectedAlarmSound)
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 38
                                    background: Rectangle { color: "#ffffff"; border.color: "#d1d5db"; radius: 4 } }
                                RowLayout {
                                    spacing: 10
                                    Layout.fillWidth: true
                                    Button { text: "Test"
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 38
                                        background: Rectangle { color: "#334155"; radius: 4 }
                                        contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 12 }
                                        onClicked: backend.testAlarm(soundBox.currentText) }
                                    Button { text: "Save"
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 38
                                        background: Rectangle { color: "#1e3a5f"; radius: 4 }
                                        contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 12 }
                                        onClicked: backend.setAlarmSound(soundBox.currentText) }
                                }
                                Label { text: backend ? backend.alarmTestStatus : ""; color: backend.alarmTestStatus.indexOf("Failed") >=0 || backend.alarmTestStatus.indexOf("Error") >=0 ? "#991b1b" : "#14532d"; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true; visible: backend.alarmTestStatus !== "" }
                            }
                        }
                        // Offline TTS bento
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 148
                            radius: 4
                            color: "#ffffff"
                            border.color: "#d1d5db"
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 12
                                RowLayout {
                                    spacing: 8
                                    Layout.fillWidth: true
                                    Rectangle { color: "#14532d"; radius: 4; Layout.preferredWidth: 4; Layout.preferredHeight: 14 }
                                    Label { text: "Offline TTS"; color: "#1e293b"; font.bold: true; font.pixelSize: 13; Layout.fillWidth: true }
                                    Rectangle { color: ttsSwitch.checked ? "#14532d" : "#64748b"; radius: 8; Layout.preferredWidth: 44; Layout.preferredHeight: 18; Label { anchors.centerIn: parent; text: ttsSwitch.checked ? "On" : "Off"; color: "white"; font.pixelSize: 10; font.bold: true } }
                                }
                                Label { text: "Announcements when queue advances"; color: "#475569"; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                RowLayout {
                                    spacing: 10
                                    Layout.fillWidth: true
                                    Label { text: "Voice announcements"; color: "#1e293b"; font.pixelSize: 13; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Switch { id: ttsSwitch
                                        checked: backend ? backend.ttsEnabled : true; onToggled: backend.setTtsEnabled(checked) }
                                }
                                Label { text: "speech-dispatcher / espeak-ng • 100% offline"; color: "#475569"; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap; elide: Text.ElideRight }
                            }
                        }
                    }
                }

                // ================= SYSTEM TAB =================
                ColumnLayout {
                    visible: admin.currentTab === "System"
                    spacing: 16
                    Layout.fillWidth: true
                    GridLayout {
                        columns: 2
                        columnSpacing: 16
                        rowSpacing: 16
                        Layout.fillWidth: true
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 160
                            radius: 4
                            color: "#ffffff"
                            border.color: "#1e3a5f"
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 8
                                RowLayout {
                                    spacing: 8
                                    Layout.fillWidth: true
                                    Rectangle { color: "#1e3a5f"
                                    radius: 4
                                    Layout.preferredWidth: 4
                                    Layout.preferredHeight: 16 }
                                    Label { text: "Bathroom Pass"
                                    color: "#1e3a5f"
                                    font.bold: true
                                    font.pixelSize: 13 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: "OVERTIME threshold"
                                    color: "#475569"
                                    font.pixelSize: 11 }
                                }
                                Label { text: "How long before OVERTIME alarm"
                                    color: "#475569"
                                    font.pixelSize: 11
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true }
                                RowLayout {
                                    spacing: 12
                                    Layout.fillWidth: true
                                    Rectangle {
                                        color: "#f1f5f9"
                                        radius: 4
                                        border.color: "#d1d5db"
                                        border.width: 1
                                        Layout.preferredWidth: 150
                                        Layout.preferredHeight: 48
                                        Label {
                                            anchors.centerIn: parent
                                            text: backend ? (Math.floor(backend.bathroomThreshold/60) + " min " + (backend.bathroomThreshold%60 < 10 ? "0" : "") + backend.bathroomThreshold%60 + " sec") : "7 min 00 sec"
                                            color: "#1e3a5f"
                                            font.pixelSize: 15
                                            font.bold: true
                                        }
                                    }
                                    Button {
                                        text: "− 1 min"
                                        Layout.preferredHeight: 44
                                        Layout.preferredWidth: 104
                                        Layout.minimumWidth: 104
                                        contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 12 }
                                        background: Rectangle { color: "#334155"
                                    radius: 4 }
                                        onClicked: backend.adjustThreshold("Bathroom", -60)
                                    }
                                    Button {
                                        text: "+ 1 min"
                                        Layout.preferredHeight: 44
                                        Layout.preferredWidth: 104
                                        Layout.minimumWidth: 104
                                        contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 12 }
                                        background: Rectangle { color: "#1e3a5f"
                                    radius: 4 }
                                        onClicked: backend.adjustThreshold("Bathroom", 60)
                                    }
                                }
                                RowLayout {
                                    spacing: 6
                                    Layout.fillWidth: true
                                    Label { text: backend ? "(" + backend.bathroomThreshold + " sec)" : "(420 sec)"
                                    color: "#475569"
                                    font.pixelSize: 11 }
                                    Label { text: "• Minimum 60 sec"
                                    color: "#334155"
                                    font.pixelSize: 11 }
                                }
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 160
                            radius: 4
                            color: "#ffffff"
                            border.color: "#14532d"
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 8
                                RowLayout {
                                    spacing: 8
                                    Layout.fillWidth: true
                                    Rectangle { color: "#14532d"
                                    radius: 4
                                    Layout.preferredWidth: 4
                                    Layout.preferredHeight: 16 }
                                    Label { text: "Water Fill Pass"
                                    color: "#14532d"
                                    font.bold: true
                                    font.pixelSize: 13 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: "Shorter threshold"
                                    color: "#475569"
                                    font.pixelSize: 11 }
                                }
                                Label { text: "Shorter limit — independent from Bathroom"
                                    color: "#475569"
                                    font.pixelSize: 11
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true }
                                RowLayout {
                                    spacing: 12
                                    Layout.fillWidth: true
                                    Rectangle {
                                        color: "#f1f5f9"
                                        radius: 4
                                        border.color: "#d1d5db"
                                        border.width: 1
                                        Layout.preferredWidth: 150
                                        Layout.preferredHeight: 48
                                        Label {
                                            anchors.centerIn: parent
                                            text: backend ? (Math.floor(backend.waterThreshold/60) + " min " + (backend.waterThreshold%60 < 10 ? "0" : "") + backend.waterThreshold%60 + " sec") : "3 min 00 sec"
                                            color: "#14532d"
                                            font.pixelSize: 15
                                            font.bold: true
                                        }
                                    }
                                    Button {
                                        text: "− 30 sec"
                                        Layout.preferredHeight: 44
                                        Layout.preferredWidth: 104
                                        Layout.minimumWidth: 104
                                        contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 12 }
                                        background: Rectangle { color: "#334155"
                                    radius: 4 }
                                        onClicked: backend.adjustThreshold("Water", -30)
                                    }
                                    Button {
                                        text: "+ 30 sec"
                                        Layout.preferredHeight: 44
                                        Layout.preferredWidth: 104
                                        Layout.minimumWidth: 104
                                        contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 12 }
                                        background: Rectangle { color: "#14532d"
                                    radius: 4 }
                                        onClicked: backend.adjustThreshold("Water", 30)
                                    }
                                }
                                RowLayout {
                                    spacing: 6
                                    Layout.fillWidth: true
                                    Label { text: backend ? "(" + backend.waterThreshold + " sec)" : "(180 sec)"
                                    color: "#475569"
                                    font.pixelSize: 11 }
                                    Label { text: "• Steps 30 sec"
                                    color: "#334155"
                                    font.pixelSize: 11 }
                                }
                            }
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 230
                        radius: 4
                        color: "#ffffff"
                        border.color: "#d1d5db"
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 10
                            Label { text: "Export & System"
                                    color: "#1e3a5f"
                                    font.bold: true
                                    font.pixelSize: 13
                                    Layout.fillWidth: true }
                            ComboBox {
                                id: exportChoice
                                model: ["Auto-Detect USB (/media)", "Local Folder"]
                                Layout.fillWidth: true
                                Layout.preferredHeight: 38
                                background: Rectangle { color: "#ffffff"; border.color: "#d1d5db"; radius: 4 }
                            }
                            Button {
                                text: "Export CSV Logs & Photos"
                                Layout.fillWidth: true
                                Layout.preferredHeight: 42
                                background: Rectangle { color: "#1e3a5f"; radius: 4 }
                                contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 12; wrapMode: Text.WordWrap }
                                onClicked: backend.exportLogs(exportChoice.currentIndex === 0 ? "usb" : "local")
                            }
                            Label {
                                text: backend ? backend.exportStatus : ""
                                color: backend.exportStatus.indexOf("failed") >= 0 ? "#991b1b" : "#14532d"
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                                font.pixelSize: 11
                                visible: backend.exportStatus !== ""
                            }
                            Rectangle { Layout.fillWidth: true; height: 1; color: "#e5e7eb" }
                            RowLayout {
                                spacing: 12
                                Layout.fillWidth: true
                                Layout.preferredHeight: 44
                                Button {
                                    text: "Exit Fullscreen"
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    background: Rectangle { color: "#ffffff"; radius: 4; border.color: "#d1d5db"; border.width: 1 }
                                    contentItem: Text { text: parent.text; color: "#1e293b"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 12; wrapMode: Text.WordWrap }
                                    onClicked: { admin.close(); backend.exitFullscreen() }
                                }
                                Button {
                                    text: "Close Application"
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    background: Rectangle { color: "#ef4444"; radius: 4 }
                                    contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 12; wrapMode: Text.WordWrap }
                                    onClicked: {
                                        if (backend.verifyQuit()) Qt.quit()
                                        else { pinField.text = ""; admin.close() }
                                    }
                                }
                            }
                        }
                    }
                }
                Item { Layout.preferredHeight: 12 }
            }
        }
    }
}
