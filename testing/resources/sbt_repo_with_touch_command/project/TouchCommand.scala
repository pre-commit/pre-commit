import sbt.Command

import java.nio.file.{Files, Paths}

object TouchCommand {
  def touchCommand = Command.args("touch", "args") { (state, args) =>
    args.map(Paths.get(_).toAbsolutePath).foreach { path =>
      println(f"Creating file: $path")
      Files.createFile(path)
    }
    state
  }
}
