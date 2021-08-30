import 'package:ansicolor/ansicolor.dart';

void main() {
    AnsiPen pen = new AnsiPen()..red();
    print("hello hello " + pen("world"));
}
