import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Dialog {
    id: qd
    title: "Get In Line"
    modal: true
    standardButtons: Dialog.NoButton
    anchors.centerIn: parent
    width: 480
    property string selectedName: ""
    property string selectedType: "Bathroom"

    ColumnLayout {
        anchors.fill: parent
        spacing: 14
        Label {
            text: "Select your name"
            color: "#1e3a5f"
            font.family: "Libre Baskerville"
            font.bold: true
            font.pixelSize: 14
        }
        ComboBox {
            id: nameBox
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            model: typeof roster !== "undefined" ? roster : []
            onCurrentTextChanged: qd.selectedName = currentText
            // Ensure popup text is dark on white
            contentItem: Text {
                text: nameBox.displayText
                color: "#1e293b"
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            background: Rectangle {
                color: "#ffffff"
                border.color: "#d1d5db"
                border.width: 1
                radius: 6
            }
        }
        Label {
            text: "Pass type"
            color: "#1e3a5f"
            font.family: "Source Sans Pro"
            font.bold: true
            font.pixelSize: 13
        }
        RowLayout {
            spacing: 16
            RadioButton {
                text: "Bathroom"
                checked: true
                onClicked: qd.selectedType="Bathroom"
                contentItem: Text {
                    text: parent.text
                    color: "#1e293b"
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: parent.indicator.width + 6
                }
            }
            RadioButton {
                text: "Water"
                onClicked: qd.selectedType="Water"
                contentItem: Text {
                    text: parent.text
                    color: "#1e293b"
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: parent.indicator.width + 6
                }
            }
        }
        RowLayout {
            spacing: 12
            Button {
                text: "Cancel"
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                background: Rectangle {
                    color: "#e5e7eb"
                    radius: 6
                    border.color: "#d1d5db"
                    border.width: 1
                }
                contentItem: Text {
                    text: parent.text
                    color: "#1e293b"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.bold: true
                }
                onClicked: qd.close()
            }
            Button {
                text: "Join Queue"
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                background: Rectangle {
                    color: "#1e3a5f"
                    radius: 6
                }
                contentItem: Text {
                    text: parent.text
                    color: "#f8f6f0"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.bold: true
                }
                onClicked: {
                    if (qd.selectedName) backend.enqueue(qd.selectedName, qd.selectedType)
                    qd.close()
                }
            }
        }
    }
    background: Rectangle {
        color: "#ffffff"
        radius: 8
        border.color: "#1e3a5f"
        border.width: 1
    }
}
