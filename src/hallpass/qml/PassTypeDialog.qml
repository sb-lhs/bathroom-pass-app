import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Dialog {
    id: dlg
    title: "Choose Pass Type"
    modal: true
    standardButtons: Dialog.NoButton
    anchors.centerIn: parent
    width: 420
    property string student: ""
    ColumnLayout {
        anchors.fill: parent
        spacing: 14
        Label {
            text: "Student: " + dlg.student
            font.family: "Libre Baskerville"
            font.pixelSize: 16
            font.bold: true
            color: "#1e3a5f"
        }
        Label {
            visible: typeof backend !== "undefined" && backend.stateMode !== "IDLE"
            text: "A pass is already out — you’ll be added to the queue"
            color: "#7f1d1d"
            font.family: "Source Sans Pro"
            font.pixelSize: 12
            font.italic: true
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
        Button {
            Layout.fillWidth: true
            height: 68
            text: "Bathroom Pass (7 min)"
            font.family: "Source Sans Pro"
            font.pixelSize: 16
            font.bold: true
            background: Rectangle {
                color: "#1e3a5f"
                radius: 6
            }
            onClicked: { if (typeof backend !== "undefined" && backend.stateMode !== "IDLE") backend.enqueue(dlg.student, "Bathroom"); else backend.selectStudent(dlg.student, "Bathroom"); dlg.close() }
        }
        Button {
            Layout.fillWidth: true
            height: 68
            text: "Water Fill Pass (3 min)"
            font.family: "Source Sans Pro"
            font.pixelSize: 16
            font.bold: true
            background: Rectangle {
                color: "#14532d"
                radius: 6
            }
            onClicked: { if (typeof backend !== "undefined" && backend.stateMode !== "IDLE") backend.enqueue(dlg.student, "Water"); else backend.selectStudent(dlg.student, "Water"); dlg.close() }
        }
        Button {
            Layout.fillWidth: true
            text: "Cancel"
            font.family: "Source Sans Pro"
            onClicked: dlg.close()
        }
    }
    background: Rectangle {
        color: "#ffffff"
        radius: 8
        border.color: "#d1d5db"
        border.width: 1
    }
}
