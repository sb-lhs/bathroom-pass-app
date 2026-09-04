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
    property string pendingTab: ""
    property bool pendingClose: false
    property var rosterDirty: ({})
    onClosed: backend.logoutAdmin()
    onVisibleChanged: if (!visible) backend.logoutAdmin()
    function hasUnsavedRosters() {
        for (var k in rosterDirty) if (rosterDirty[k]) return true
        return false
    }
    function trySwitchTab(newTab) {
        if (hasUnsavedRosters()) { pendingTab = newTab; unsavedDialog.open() } else { currentTab = newTab }
    }
    function tryCloseAdmin() {
        if (hasUnsavedRosters()) { pendingClose = true; unsavedDialog.open() } else { admin.close() }
    }

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
                        onClicked: admin.trySwitchTab(modelData.key)
                    }
                }
                Item { Layout.fillWidth: true }
                Button {
                    text: "✕ Close"
                    Layout.fillHeight: true
                    Layout.preferredWidth: 100
                    background: Rectangle { color: "#334155"
                                    radius: 4 }
                    onClicked: admin.tryCloseAdmin()
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
                        Layout.preferredHeight: 170
                        radius: 4
                        color: backend.simpleMode ? "#eff6ff" : "#ffffff"
                        border.color: backend.simpleMode ? "#3b82f6" : "#d1d5db"
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 10
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                Label { text: "Simple Mode (All Day, All Students)"; color: "#1e3a5f"; font.bold: true; font.pixelSize: 13; Layout.fillWidth: true }
                                Switch {
                                    id: simpleModeSwitch
                                    Binding on checked { value: backend ? backend.simpleMode : false }
                                    onToggled: backend.setSimpleMode(checked)
                                }
                            }
                            Label {
                                text: "When on, the bell schedule and A/B sorting are hidden — one roster shows for the whole day. Works for any school size or sorting."
                                color: "#475569"
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                visible: backend.simpleMode
                                Label { text: "Simple Roster:"; color: "#1e3a5f"; font.pixelSize: 12 }
                                TextField {
                                    id: simpleRosterField
                                    text: backend.simpleRosterText
                                    placeholderText: "alice, bob, carol"
                                    color: "#0f172a"
                                    placeholderTextColor: "#64748b"
                                    selectionColor: "#3b82f6"
                                    selectedTextColor: "white"
                                    Layout.fillWidth: true
                                    font.pixelSize: 12
                                    background: Rectangle { color: "#ffffff"; border.color: "#475569"; border.width: 1; radius: 4 }
                                    onEditingFinished: backend.setSimpleRoster(text)
                                }
                                Button { text: "Save"; onClicked: backend.setSimpleRoster(simpleRosterField.text); Layout.preferredWidth: 80 }
                            }
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 460
                        radius: 4
                        color: "#ffffff"
                        border.color: "#d1d5db"
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 10
                            Label { text: "Weekday → Bell Template + Day Letter (set-and-forget)"
                                    color: "#1e3a5f"
                                    font.bold: true
                                    font.pixelSize: 13
                                    Layout.fillWidth: true }
                            Label { text: "Which bell times + Everyday/A/B each weekday uses when no date override. Keep all Regular/Everyday, or set Wednesday to Late Start/A etc. Letter picks which roster variant shows."
                                    color: "#475569"
                                    font.pixelSize: 11
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true }
                            GridLayout {
                                columns: 1
                                columnSpacing: 12
                                rowSpacing: 8
                                Layout.fillWidth: true
                                Repeater {
                                    model: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                                    delegate: RowLayout {
                                        spacing: 8
                                        Layout.fillWidth: true
                                        Label { text: modelData; color: "#1e293b"; Layout.preferredWidth: 85; font.pixelSize: 13 }
                                        ComboBox {
                                            id: wtBox
                                            model: Object.keys(backend.templates).length ? Object.keys(backend.templates) : ["Regular"]
                                            currentIndex: Math.max(0, Object.keys(backend.templates).indexOf(backend.weekdayTemplates[modelData] || "Regular"))
                                            onActivated: backend.setWeekdayTemplate(modelData, currentText)
                                            Layout.preferredWidth: 150
                                            Layout.preferredHeight: 36
                                            Layout.fillWidth: true
                                            background: Rectangle { color: "#ffffff"; border.color: "#1e3a5f"; border.width: 1; radius: 4 }
                                            contentItem: Text { text: parent.displayText; color: "#1e293b"; verticalAlignment: Text.AlignVCenter; leftPadding: 10; font.pixelSize: 12 }
                                            delegate: ItemDelegate { width: parent.width; contentItem: Text { text: modelData; color: "#0f172a"; font.pixelSize: 12 } background: Rectangle { color: highlighted ? "#e2e8f0" : "#ffffff" } highlighted: wtBox.highlightedIndex === index }
                                        }
                                        ComboBox {
                                            id: wlBox
                                            model: ["Everyday", "A", "B"]
                                            currentIndex: Math.max(0, ["Everyday","A","B"].indexOf(backend.weekdayLetters[modelData] || "Everyday"))
                                            onActivated: backend.setWeekdayLetter(modelData, currentText)
                                            Layout.preferredWidth: 110
                                            Layout.preferredHeight: 36
                                            background: Rectangle { color: "#ffffff"; border.color: "#475569"; border.width: 1; radius: 4 }
                                            contentItem: Text { text: parent.displayText; color: "#1e293b"; verticalAlignment: Text.AlignVCenter; leftPadding: 10; font.pixelSize: 12 }
                                            delegate: ItemDelegate { width: parent.width; contentItem: Text { text: modelData; color: "#0f172a"; font.pixelSize: 12 } background: Rectangle { color: highlighted ? "#e2e8f0" : "#ffffff" } highlighted: wlBox.highlightedIndex === index }
                                        }
                                    }
                                }
                            }
                            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: "#e2e8f0" }
                            Label { text: "Custom Day (overrides calendar & weekday)"; color: "#1e3a5f"; font.bold: true; font.pixelSize: 12; Layout.fillWidth: true }
                            Label { text: "One-off: e.g. 2026-09-03 → B or Regular Wednesday:A. Custom abrogates calendar."; color: "#64748b"; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            RowLayout {
                                spacing: 8
                                Layout.fillWidth: true
                                TextField { id: customDateField; placeholderText: "YYYY-MM-DD"; color: "#0f172a"; placeholderTextColor: "#64748b"; selectionColor: "#3b82f6"; selectedTextColor: "white"; Layout.preferredWidth: 130; Layout.preferredHeight: 36; font.pixelSize: 12; background: Rectangle { color: "#ffffff"; border.color: "#475569"; radius: 4 } }
                                ComboBox { id: customTemplateBox; model: Object.keys(backend.templates).length ? Object.keys(backend.templates) : ["Regular"]; Layout.preferredWidth: 150; Layout.preferredHeight: 36; background: Rectangle { color: "#ffffff"; border.color: "#64748b"; radius: 4 } contentItem: Text { text: parent.displayText; color: "#1e293b"; verticalAlignment: Text.AlignVCenter; leftPadding: 8; font.pixelSize: 12 } delegate: ItemDelegate { width: parent.width; contentItem: Text { text: modelData; color: "#0f172a"; font.pixelSize: 12 } background: Rectangle { color: highlighted ? "#e2e8f0" : "#ffffff" } } }
                                ComboBox { id: customLetterBox; model: ["Everyday", "A", "B"]; Layout.preferredWidth: 90; Layout.preferredHeight: 36; background: Rectangle { color: "#ffffff"; border.color: "#64748b"; radius: 4 } contentItem: Text { text: parent.displayText; color: "#1e293b"; verticalAlignment: Text.AlignVCenter; leftPadding: 8; font.pixelSize: 12 } delegate: ItemDelegate { width: parent.width; contentItem: Text { text: modelData; color: "#0f172a"; font.pixelSize: 12 } background: Rectangle { color: highlighted ? "#e2e8f0" : "#ffffff" } } }
                                Button {
                                    text: "Set"
                                    Layout.preferredWidth: 60
                                    Layout.preferredHeight: 36
                                    background: Rectangle { color: "#1e3a5f"; radius: 4 }
                                    contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 12 }
                                    onClicked: {
                                        if (customDateField.text.length === 10) {
                                            backend.setCustomDayTemplate(customDateField.text, customTemplateBox.currentText)
                                            backend.setCustomDayLetter(customDateField.text, customLetterBox.currentText)
                                        }
                                    }
                                }
                                Button {
                                    text: "Clear"
                                    Layout.preferredWidth: 60
                                    Layout.preferredHeight: 36
                                    background: Rectangle { color: "#ffffff"; radius: 4; border.color: "#64748b" }
                                    contentItem: Text { text: parent.text; color: "#334155"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.pixelSize: 12 }
                                    onClicked: if (customDateField.text.length === 10) backend.clearCustomDay(customDateField.text)
                                }
                            }
                            Label { text: "Calendar Import — source of truth (replaces all dates)"; color: "#1e3a5f"; font.bold: true; font.pixelSize: 12; Layout.fillWidth: true }
                            RowLayout {
                                spacing: 8
                                Layout.fillWidth: true
                                Button {
                                    text: "Import CSV"
                                    Layout.preferredWidth: 110
                                    Layout.preferredHeight: 36
                                    background: Rectangle { color: "#334155"; radius: 4 }
                                    contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 12 }
                                    onClicked: calendarCsvDialog.open()
                                }
                                Button {
                                    text: "Import ICS"
                                    Layout.preferredWidth: 110
                                    Layout.preferredHeight: 36
                                    background: Rectangle { color: "#334155"; radius: 4 }
                                    contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 12 }
                                    onClicked: calendarIcsDialog.open()
                                }
                                Label {
                                    text: Object.keys(backend.dateOverrides).length + " dates loaded"
                                    color: "#475569"
                                    font.pixelSize: 11
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                            }
                            Label {
                                text: backend ? backend.rosterImportStatus : ""
                                color: backend.rosterImportStatus.indexOf("failed")>=0 ? "#991b1b" : "#14532d"
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                                font.pixelSize: 10
                                visible: backend.rosterImportStatus !== "" && admin.currentTab==="Schedules"
                            }
                        }
                    }
                    Rectangle {
                        id: manualScheduleRect
                        Layout.fillWidth: true
                        Layout.preferredHeight: manualScheduleCol.implicitHeight + 32
                        radius: 4
                        color: "#ffffff"
                        border.color: "#1e3a5f"
                        border.width: 1
                        ColumnLayout {
                            id: manualScheduleCol
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12
                            RowLayout {
                                spacing: 8
                                Layout.fillWidth: true
                                Rectangle { color: "#1e3a5f"; radius: 4; Layout.preferredWidth: 4; Layout.preferredHeight: 16 }
                                Label { text: "Bell Templates — Manual Schedule (no import needed)"
                                    color: "#1e3a5f"
                                    font.bold: true
                                    font.pixelSize: 14
                                    Layout.fillWidth: true }
                                Label { text: Object.keys(backend.templates).length + " templates"; color: "#475569"; font.pixelSize: 11 }
                            }
                            Label { text: "Create any bell schedule — Regular, Wednesday, Half Day, etc. Each template has its own blocks/times. Pick the weekday template above to use it without any calendar file. Names are yours — not baked in."; color: "#475569"; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 11 }
                            RowLayout {
                                spacing: 8
                                Layout.fillWidth: true
                                TextField { id: newTemplateName; placeholderText: "New template name (e.g., Late Start)"; color: "#0f172a"; placeholderTextColor: "#64748b"; selectionColor: "#3b82f6"; selectedTextColor: "white"; Layout.fillWidth: true; Layout.preferredHeight: 36; font.pixelSize: 12; background: Rectangle { color: "#ffffff"; border.color: "#475569"; border.width: 1; radius: 4 } }
                                ComboBox { id: copyFromTemplate; model: Object.keys(backend.templates).length ? Object.keys(backend.templates) : ["Regular"]; Layout.preferredWidth: 150; Layout.preferredHeight: 36; background: Rectangle { color: "#ffffff"; border.color: "#64748b"; radius: 4 } contentItem: Text { text: "Copy from " + parent.displayText; color: "#1e293b"; verticalAlignment: Text.AlignVCenter; leftPadding: 8; font.pixelSize: 11 } }
                                Button {
                                    text: "Create"
                                    Layout.preferredWidth: 80
                                    Layout.preferredHeight: 36
                                    background: Rectangle { color: "#14532d"; radius: 4 }
                                    contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 12 }
                                    onClicked: if (backend.createTemplate(newTemplateName.text, copyFromTemplate.currentText)) newTemplateName.text = ""
                                }
                            }
                            ColumnLayout {
                                spacing: 16
                                Layout.fillWidth: true
                                Repeater {
                                    model: Object.keys(backend.templates)
                                    delegate: Rectangle {
                                        property string tmplName: modelData
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: tmplInner.implicitHeight + 24
                                        radius: 6
                                        color: "#f8fafc"
                                        border.color: modelData === "Simple" ? "#3b82f6" : "#cbd5e1"
                                        border.width: 1
                                        ColumnLayout {
                                            id: tmplInner
                                            anchors.fill: parent
                                            anchors.margins: 12
                                            spacing: 8
                                            RowLayout {
                                                Layout.fillWidth: true
                                                spacing: 8
                                                Label { text: modelData; color: modelData === "Simple" ? "#1d4ed8" : "#1e3a5f"; font.bold: true; font.pixelSize: 13; Layout.fillWidth: true; elide: Text.ElideRight }
                                                Label { text: backend.getDisplayBlocks(modelData).length + " blocks"; color: "#475569"; font.pixelSize: 11 }
                                                Button {
                                                    text: "Delete Template"
                                                    visible: Object.keys(backend.templates).length > 1 && modelData !== "Simple"
                                                    Layout.preferredWidth: 120
                                                    Layout.preferredHeight: 30
                                                    background: Rectangle { color: "#ffffff"; radius: 4; border.color: "#991b1b" }
                                                    contentItem: Text { text: parent.text; color: "#991b1b"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.pixelSize: 11 }
                                                    onClicked: backend.deleteTemplate(modelData)
                                                }
                                            }
                                            Repeater {
                                                model: backend.templates ? backend.getDisplayBlocks(tmplName) : []
                                                delegate: RowLayout {
                                                    spacing: 6
                                                    Layout.fillWidth: true
                                                    property string tName: modelData.display_name
                                                    property string tDisplay: modelData.display_name
                                                    TextField { id: tBlockName; text: modelData.is_custom ? modelData.display_name : ""; placeholderText: modelData.display_name; color: "#0f172a"; placeholderTextColor: "#64748b"; selectionColor: "#3b82f6"; selectedTextColor: "white"; Layout.preferredWidth: 160; Layout.preferredHeight: 34; font.pixelSize: 11; background: Rectangle { color: modelData.is_custom ? "#ffffff" : "#f1f5f9"; border.color: "#334155"; border.width: 1; radius: 4 } }
                                                    TextField { id: tBlockStart; text: modelData.start; color: "#0f172a"; selectionColor: "#3b82f6"; selectedTextColor: "white"; Layout.preferredWidth: 70; Layout.preferredHeight: 34; font.pixelSize: 11; background: Rectangle { color: "#ffffff"; border.color: "#334155"; border.width: 1; radius: 4 } }
                                                    Label { text: "→"; color: "#0f172a"; font.pixelSize: 12; font.bold: true }
                                                    TextField { id: tBlockEnd; text: modelData.end; color: "#0f172a"; selectionColor: "#3b82f6"; selectedTextColor: "white"; Layout.preferredWidth: 70; Layout.preferredHeight: 34; font.pixelSize: 11; background: Rectangle { color: "#ffffff"; border.color: "#334155"; border.width: 1; radius: 4 } }
                                                    Button {
                                                        text: "Save"
                                                        Layout.preferredWidth: 54
                                                        Layout.preferredHeight: 34
                                                        background: Rectangle { color: "#1e3a5f"; radius: 4 }
                                                        contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.pixelSize: 11; font.bold: true }
                                                        onClicked: backend.updateBlockInTemplate(tmplName, tName, tBlockName.text, tBlockStart.text, tBlockEnd.text)
                                                    }
                                                    Button {
                                                        text: "X"
                                                        Layout.preferredWidth: 34
                                                        Layout.preferredHeight: 34
                                                        background: Rectangle { color: "#ffffff"; radius: 4; border.color: "#991b1b" }
                                                        contentItem: Text { text: parent.text; color: "#991b1b"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 11 }
                                                        onClicked: backend.deleteBlockFromTemplate(tmplName, tName)
                                                    }
                                                }
                                            }
                                            RowLayout {
                                                spacing: 6
                                                Layout.fillWidth: true
                                                TextField { id: addTName; placeholderText: "empty=Block N or Lunch"; color: "#0f172a"; placeholderTextColor: "#64748b"; selectionColor: "#3b82f6"; selectedTextColor: "white"; Layout.preferredWidth: 140; Layout.preferredHeight: 34; font.pixelSize: 11; background: Rectangle { color: "#ffffff"; border.color: "#475569"; border.width: 1; radius: 4 } }
                                                TextField { id: addTStart; placeholderText: "08:00"; text: "08:00"; color: "#0f172a"; placeholderTextColor: "#64748b"; selectionColor: "#3b82f6"; selectedTextColor: "white"; Layout.preferredWidth: 70; Layout.preferredHeight: 34; font.pixelSize: 11; background: Rectangle { color: "#ffffff"; border.color: "#475569"; border.width: 1; radius: 4 } }
                                                Label { text: "→"; color: "#0f172a"; font.pixelSize: 12; font.bold: true }
                                                TextField { id: addTEnd; placeholderText: "09:20"; text: "09:20"; color: "#0f172a"; placeholderTextColor: "#64748b"; selectionColor: "#3b82f6"; selectedTextColor: "white"; Layout.preferredWidth: 70; Layout.preferredHeight: 34; font.pixelSize: 11; background: Rectangle { color: "#ffffff"; border.color: "#475569"; border.width: 1; radius: 4 } }
                                                Button {
                                                    text: "Add to " + tmplName
                                                    Layout.fillWidth: true
                                                    Layout.preferredHeight: 34
                                                    background: Rectangle { color: "#334155"; radius: 4 }
                                                    contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.pixelSize: 11; font.bold: true }
                                                    onClicked: if (backend.addBlockToTemplate(tmplName, addTName.text, addTStart.text, addTEnd.text)) addTName.text=""
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    // Legacy quick Add Block (hidden — templates are source of truth)
                    Rectangle {
                        visible: false
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
                                ComboBox { id: newDayType; model: ["Everyday", "A", "B"]; Layout.preferredWidth: 110; Layout.preferredHeight: 38; background: Rectangle { color: "#ffffff"; border.color: "#1e3a5f"; border.width: 1; radius: 4 } contentItem: Text { text: parent.displayText; color: "#1e293b"; verticalAlignment: Text.AlignVCenter; leftPadding: 10; font.pixelSize: 13 } }
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
                    // Dynamic blocks list — hidden (legacy)
                    Rectangle {
                        visible: false
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
                        visible: false
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
                                            model: ["Everyday", "A", "B"]
                                            currentIndex: Math.max(0, ["Everyday", "A", "B"].indexOf(modelData.day_type || "Everyday"))
                                            Layout.preferredWidth: 110
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
                                Label { text: backend.getAllBlockNames().length + " blocks (detached — assign to any Block name)"
                                    color: "#475569"
                                    font.pixelSize: 11 }
                            }
                            Label {
                                text: "Each block shows 3 rosters: Everyday (daily, used when A/B empty) and A/B (shown when weekday letter is A/B). Rosters are detached — they live on the Block name, not on times. Times → Block N via position (insert-shift)."
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
                        spacing: 20
                        Layout.fillWidth: true
                        Repeater {
                            id: rosterRepeater
                            model: backend.structuredRosters ? backend.getAllBlockNames() : backend.getAllBlockNames()
                            delegate: Rectangle {
                                property string blockName: modelData
                                Layout.fillWidth: true
                                Layout.preferredHeight: 190
                                radius: 6
                                color: "#ffffff"
                                border.color: "#d1d5db"
                                border.width: 2
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 10
                                    Label { text: blockName
                                        color: "#1e3a5f"
                                        font.bold: true
                                        font.pixelSize: 14
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                        wrapMode: Text.NoWrap }
                                    RowLayout {
                                        spacing: 10
                                        Layout.fillWidth: true
                                        Rectangle {
                                            color: "#334155"
                                            radius: 6
                                            border.color: "#334155"
                                            border.width: 1
                                            Layout.preferredWidth: 110
                                            Layout.preferredHeight: 22
                                            Label { anchors.centerIn: parent; text: blockName.indexOf("Block")===0 ? "Auto Block" : "Custom Block"; color: "white"; font.pixelSize: 10; font.bold: true; elide: Text.ElideRight }
                                        }
                                        Item { Layout.fillWidth: true }
                                        Rectangle {
                                            color: "#f1f5f9"
                                            radius: 4
                                            border.color: "#d1d5db"
                                            border.width: 1
                                            Layout.preferredWidth: 110
                                            Layout.preferredHeight: 22
                                            Label { anchors.centerIn: parent; text: (backend.structuredRosters[blockName] ? ((backend.structuredRosters[blockName]["Everyday"]||[]).length + (backend.structuredRosters[blockName]["A"]||[]).length + (backend.structuredRosters[blockName]["B"]||[]).length) : (backend.flatRosters[blockName] ? backend.flatRosters[blockName].length : 0)) + " total"; color: "#1e293b"; font.pixelSize: 11; font.bold: true; elide: Text.ElideRight }
                                        }
                                    }
                                    RowLayout {
                                        spacing: 6
                                        Layout.fillWidth: true
                                        Label { text: "Roster:"; color: "#334155"; font.pixelSize: 11; font.bold: true }
                                        ComboBox {
                                            id: variantBox
                                            model: ["Everyday", "A", "B"]
                                            currentIndex: 0
                                            Layout.preferredWidth: 110
                                            Layout.preferredHeight: 30
                                            background: Rectangle { color: "#ffffff"; border.color: "#64748b"; radius: 4 }
                                            contentItem: Text { text: parent.displayText; color: "#1e293b"; verticalAlignment: Text.AlignVCenter; leftPadding: 8; font.pixelSize: 11; font.bold: true }
                                            delegate: ItemDelegate { width: parent.width; contentItem: Text { text: modelData; color: "#0f172a"; font.pixelSize: 11 } background: Rectangle { color: highlighted ? "#e2e8f0" : "#ffffff"} }
                                            onCurrentTextChanged: {
                                                var t = backend.getRosterForBlockVariant(blockName, currentText)
                                                rosterField.originalText = t
                                                rosterField.text = t
                                                var mm = admin.rosterDirty
                                                mm[blockName + ":" + currentText] = false
                                                admin.rosterDirty = mm
                                            }
                                        }
                                        Label {
                                            text: variantBox.currentText === "Everyday" ? "• daily — shows when A/B empty" : variantBox.currentText === "A" ? "• A days" : "• B days"
                                            color: "#64748b"
                                            font.pixelSize: 10
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                        }
                                    }
                                    TextField {
                                        id: rosterField
                                        objectName: "rosterField"
                                        property string originalText: backend.getRosterForBlockVariant(blockName, variantBox.currentText)
                                        text: originalText
                                        placeholderText: variantBox.currentText === "Everyday" ? "Everyday — e.g., Alex, Sam" : variantBox.currentText + " — e.g., Alex for " + variantBox.currentText
                                        color: "#1e293b"
                                        placeholderTextColor: "#64748b"
                                        background: Rectangle { color: rosterField.text !== rosterField.originalText ? "#fef3c7" : "#ffffff"; border.color: rosterField.text !== rosterField.originalText ? "#f59e0b" : "#d1d5db"; radius: 4; border.width: rosterField.text !== rosterField.originalText ? 2 : 1 }
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 38
                                        font.pixelSize: 12
                                        onTextChanged: {
                                            var m = admin.rosterDirty
                                            m[blockName + ":" + variantBox.currentText] = (text !== originalText)
                                            admin.rosterDirty = m
                                        }
                                        Component.onCompleted: {
                                            var m = admin.rosterDirty
                                            m[blockName + ":" + variantBox.currentText] = false
                                            admin.rosterDirty = m
                                        }
                                    }
                                    Label {
                                        visible: rosterField.text !== rosterField.originalText
                                        text: "● Unsaved changes"
                                        color: "#d97706"
                                        font.pixelSize: 10
                                        font.bold: true
                                        Layout.fillWidth: true
                                    }
                                    RowLayout {
                                        spacing: 8
                                        Layout.fillWidth: true
                                        Button {
                                            text: "Save Roster"
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 36
                                            background: Rectangle { color: "#1e3a5f"; radius: 4 }
                                            contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 11 }
                                            onClicked: {
                                                if (backend.setRosterForBlockVariant(blockName, variantBox.currentText, rosterField.text)) {
                                                    rosterField.originalText = rosterField.text
                                                    var m = admin.rosterDirty
                                                    m[blockName + ":" + variantBox.currentText] = false
                                                    admin.rosterDirty = m
                                                }
                                            }
                                        }
                                        Button {
                                            text: "Import CSV"
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 36
                                            background: Rectangle { color: "#334155"; radius: 4 }
                                            contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 11 }
                                            onClicked: { admin.pendingRosterBlock = blockName; rosterFileDialog.open() }
                                        }
                                        Button {
                                            text: "Delete All"
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 36
                                            background: Rectangle { color: "#ffffff"; radius: 4; border.color: "#991b1b"; border.width: 1 }
                                            contentItem: Text { text: parent.text; color: "#991b1b"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true; font.pixelSize: 11 }
                                            onClicked: { deleteConfirmDialog.blockName = blockName; deleteConfirmDialog.open() }
                                        }
                                    }
                                    Label {
                                        text: backend.rosterImportStatus
                                        color: backend.rosterImportStatus.indexOf("failed")>=0 || backend.rosterImportStatus.indexOf("Failed")>=0 ? "#991b1b" : "#14532d"
                                        font.pixelSize: 10
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                        visible: backend.rosterImportStatus !== "" && backend.rosterImportStatus.indexOf(blockName) >= 0
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
                            if (backend.importRosterForBlock(selectedFile, admin.pendingRosterBlock)) {
                                var m = admin.rosterDirty
                                m[admin.pendingRosterBlock] = false
                                admin.rosterDirty = m
                            }
                        }
                    }
                    FileDialog {
                        id: calendarCsvDialog
                        title: "Select Calendar CSV (date,type)"
                        nameFilters: ["CSV files (*.csv)"]
                        onAccepted: backend.importDateOverrides(selectedFile, "csv")
                    }
                    FileDialog {
                        id: calendarIcsDialog
                        title: "Select Calendar ICS"
                        nameFilters: ["ICS files (*.ics)"]
                        onAccepted: backend.importDateOverrides(selectedFile, "ics")
                    }
                    Dialog {
                        id: deleteConfirmDialog
                        property string blockName: ""
                        title: "Delete All?"
                        modal: true
                        anchors.centerIn: parent
                        width: 420
                        height: 200
                        standardButtons: Dialog.NoButton
                        background: Rectangle { color: "#ffffff"; radius: 8; border.color: "#d1d5db" }
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12
                            Label { text: "Delete all students from " + deleteConfirmDialog.blockName + "?" ; color: "#1e293b"; font.bold: true; font.pixelSize: 14; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            Label { text: "This cannot be undone. The block will be empty until you add or import again."; color: "#475569"; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            RowLayout {
                                spacing: 12
                                Layout.fillWidth: true
                                Button {
                                    text: "Cancel"
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 44
                                    background: Rectangle { color: "#ffffff"; radius: 4; border.color: "#d1d5db"; border.width: 1 }
                                    contentItem: Text { text: parent.text; color: "#1e293b"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true }
                                    onClicked: deleteConfirmDialog.close()
                                }
                                Button {
                                    text: "Delete All"
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 44
                                    background: Rectangle { color: "#991b1b"; radius: 4 }
                                    contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true }
                                    onClicked: {
                                        backend.setRosterForBlock(deleteConfirmDialog.blockName, "")
                                        var m = admin.rosterDirty
                                        m[deleteConfirmDialog.blockName] = false
                                        admin.rosterDirty = m
                                        deleteConfirmDialog.close()
                                    }
                                }
                            }
                        }
                    }
                    Dialog {
                        id: unsavedDialog
                        title: "Unsaved Rosters"
                        modal: true
                        anchors.centerIn: parent
                        width: 460
                        height: 210
                        standardButtons: Dialog.NoButton
                        background: Rectangle { color: "#ffffff"; radius: 8; border.color: "#d1d5db" }
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12
                            Label { text: "You have unsaved roster changes."; color: "#1e293b"; font.bold: true; font.pixelSize: 14; Layout.fillWidth: true }
                            Label { text: "If you leave now, your edits will be lost. Save each roster with Save Roster first."; color: "#475569"; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            RowLayout {
                                spacing: 12
                                Layout.fillWidth: true
                                Button {
                                    text: "Stay"
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 44
                                    background: Rectangle { color: "#ffffff"; radius: 4; border.color: "#d1d5db"; border.width: 1 }
                                    contentItem: Text { text: parent.text; color: "#1e293b"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true }
                                    onClicked: { admin.pendingTab=""; admin.pendingClose=false; unsavedDialog.close() }
                                }
                                Button {
                                    text: "Discard & Leave"
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 44
                                    background: Rectangle { color: "#991b1b"; radius: 4 }
                                    contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true }
                                    onClicked: {
                                        // Clear dirty flags and proceed
                                        admin.rosterDirty = ({})
                                        unsavedDialog.close()
                                        if (admin.pendingClose) { admin.pendingClose=false; admin.pendingTab=""; admin.close() }
                                        else if (admin.pendingTab !== "") { var t=admin.pendingTab; admin.pendingTab=""; admin.currentTab=t }
                                    }
                                }
                            }
                        }
                    }
                    Dialog {
                        id: cameraPickerDialog
                        title: "Choose Camera — Faces Student at Screen"
                        modal: true
                        anchors.centerIn: parent
                        width: 480
                        height: 360
                        standardButtons: Dialog.NoButton
                        background: Rectangle { color: "#ffffff"; radius: 8; border.color: "#1e3a5f"; border.width: 2 }
                        visible: backend.needsCameraPicker && admin.visible && backend.isAdminAuthenticated
                        onVisibleChanged: if (visible) cameraPickerBox.currentIndex = Math.max(0, backend.availableCameraIndices.indexOf(backend.selectedCameraIndex))
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12
                            Rectangle { color: "#1e3a5f"; radius: 4; Layout.fillWidth: true; Layout.preferredHeight: 4 }
                            Label { text: "Multiple cameras found — pick the one facing the student at the screen."; color: "#1e293b"; font.bold: true; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            Label { text: "This is shown once on first login when multiple cameras exist. Change anytime in Photos → Camera."; color: "#475569"; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            ComboBox {
                                id: cameraPickerBox
                                model: backend ? backend.availableCameraIndices : [0]
                                Layout.fillWidth: true
                                Layout.preferredHeight: 44
                                background: Rectangle { color: "#ffffff"; border.color: "#1e3a5f"; border.width: 2; radius: 4 }
                                contentItem: Text { text: "Camera " + parent.displayText; color: "#1e293b"; verticalAlignment: Text.AlignVCenter; leftPadding: 12; font.pixelSize: 14; font.bold: true }
                            }
                            RowLayout {
                                spacing: 12
                                Layout.fillWidth: true
                                Button {
                                    text: "Test"
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 44
                                    background: Rectangle { color: "#334155"; radius: 4 }
                                    contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true }
                                    onClicked: { backend.setSelectedCameraIndex(parseInt(cameraPickerBox.currentText)); var p = backend.testCameraCapture(); if (p !== "") backend.refreshPhotos() }
                                }
                                Button {
                                    text: "Use This Camera"
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 44
                                    background: Rectangle { color: "#14532d"; radius: 4 }
                                    contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true }
                                    onClicked: { backend.setSelectedCameraIndex(parseInt(cameraPickerBox.currentText)); backend.markCameraPickerShown(); cameraPickerDialog.close() }
                                }
                            }
                            Button {
                                text: "Skip — Keep Camera " + backend.selectedCameraIndex
                                Layout.fillWidth: true
                                Layout.preferredHeight: 36
                                background: Rectangle { color: "#ffffff"; radius: 4; border.color: "#d1d5db"; border.width: 1 }
                                contentItem: Text { text: parent.text; color: "#475569"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.pixelSize: 11 }
                                onClicked: { backend.markCameraPickerShown(); cameraPickerDialog.close() }
                            }
                        }
                    }
                }

                // ================= PHOTOS TAB =================
                ColumnLayout {
                    visible: admin.currentTab === "Photos"
                    spacing: 16
                    Layout.fillWidth: true
                    Rectangle {
                        id: photoAuditRect
                        Layout.fillWidth: true
                        Layout.preferredHeight: photoAuditCol.implicitHeight + 32
                        radius: 4
                        color: "#ffffff"
                        border.color: "#d1d5db"
                        ColumnLayout {
                            id: photoAuditCol
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
                            id: cameraBoxRect
                            Layout.fillWidth: true
                            Layout.preferredHeight: cameraBoxCol.implicitHeight + 24
                            radius: 4
                            color: "#fef2f2"
                            border.color: "#fecaca"
                            border.width: 1
                            ColumnLayout {
                                id: cameraBoxCol
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 6
                                RowLayout {
                                    spacing: 6
                                    Layout.fillWidth: true
                                    Label { text: "Camera"; color: "#991b1b"; font.bold: true; font.pixelSize: 12; Layout.fillWidth: true }
                                    Rectangle { color: backend.selectedCameraIndex !== 0 ? "#7c3aed" : "#1e3a5f"; radius: 4; Layout.preferredWidth: 52; Layout.preferredHeight: 18; Label { anchors.centerIn: parent; text: "cam " + backend.selectedCameraIndex; color: "white"; font.pixelSize: 10; font.bold: true } }
                                }
                                ComboBox {
                                    id: cameraBox
                                    model: backend ? backend.availableCameraIndices : [0]
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 32
                                    background: Rectangle { color: "#ffffff"; border.color: "#991b1b"; radius: 4; border.width: 1 }
                                    contentItem: Text { text: "Camera " + parent.displayText + (parent.displayText == backend.selectedCameraIndex ? " ✓" : ""); color: "#0f172a"; verticalAlignment: Text.AlignVCenter; leftPadding: 10; font.pixelSize: 11 }
                                    delegate: ItemDelegate { width: parent.width; contentItem: Text { text: "Camera " + modelData; color: "#0f172a"; font.pixelSize: 11; verticalAlignment: Text.AlignVCenter } background: Rectangle { color: highlighted ? "#e2e8f0" : "#ffffff" } highlighted: cameraBox.highlightedIndex === index }
                                    Component.onCompleted: currentIndex = Math.max(0, backend.availableCameraIndices.indexOf(backend.selectedCameraIndex))
                                    onActivated: backend.setSelectedCameraIndex(parseInt(currentText))
                                }
                                RowLayout {
                                    spacing: 8
                                    Layout.fillWidth: true
                                    Button {
                                        text: "Test Selected"
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
                                Label { text: "Pick the camera facing the student at the screen. First login shows picker if multiple."; color: "#7f1d1d"; font.pixelSize: 9; Layout.fillWidth: true; wrapMode: Text.WordWrap }
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
                                    background: Rectangle { color: "#ffffff"; border.color: "#475569"; border.width: 1; radius: 4 }
                                    contentItem: Text { text: parent.displayText; color: "#0f172a"; verticalAlignment: Text.AlignVCenter; leftPadding: 12; font.pixelSize: 12; elide: Text.ElideRight }
                                    delegate: ItemDelegate { width: parent.width; contentItem: Text { text: modelData; color: "#0f172a"; font.pixelSize: 12; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter } background: Rectangle { color: highlighted ? "#e2e8f0" : "#ffffff" } highlighted: soundBox.highlightedIndex === index }
                                    popup: Popup { y: soundBox.height - 1; width: soundBox.width; implicitHeight: contentItem.implicitHeight; padding: 1; contentItem: ListView { clip: true; implicitHeight: contentHeight; model: soundBox.popup.visible ? soundBox.delegateModel : null } background: Rectangle { color: "#ffffff"; border.color: "#475569"; radius: 4 } } }
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
                                background: Rectangle { color: "#ffffff"; border.color: "#475569"; border.width: 1; radius: 4 }
                                contentItem: Text { text: parent.displayText; color: "#0f172a"; verticalAlignment: Text.AlignVCenter; leftPadding: 12; font.pixelSize: 12; elide: Text.ElideRight }
                                delegate: ItemDelegate { width: parent.width; contentItem: Text { text: modelData; color: "#0f172a"; font.pixelSize: 12; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter } background: Rectangle { color: highlighted ? "#e2e8f0" : "#ffffff" } highlighted: exportChoice.highlightedIndex === index }
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
