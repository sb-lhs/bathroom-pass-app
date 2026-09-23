import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Window {
    id: splashWindow
    visible: true
    width: 1280
    height: 800
    visibility: Window.FullScreen
    color: "#1e3a5f"
    title: "Hall Pass"

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 18
        Label {
            text: "HALL PASS"
            color: "#f8f6f0"
            font.family: "Libre Baskerville"
            font.pixelSize: 72
            font.bold: true
            font.letterSpacing: 2
            horizontalAlignment: Text.AlignHCenter
            Layout.fillWidth: true
        }
        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 320
            Layout.preferredHeight: 2
            color: "#e2e8f0"
        }
        Label {
            text: splash.status
            color: "#e2e8f0"
            font.family: "Source Sans Pro"
            font.pixelSize: 22
            horizontalAlignment: Text.AlignHCenter
            Layout.fillWidth: true
        }
    }
}
