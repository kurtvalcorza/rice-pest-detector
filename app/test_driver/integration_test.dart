// Host-side driver for `flutter drive` runs of integration_test/ (lets device flags such as
// --no-enable-impeller be passed, which `flutter test` does not accept).
import 'package:integration_test/integration_test_driver.dart';

Future<void> main() => integrationDriver();
