import TouchCommand._

lazy val root = (project in file("."))
  .settings(
    commands ++= Seq(touchCommand)
  )
