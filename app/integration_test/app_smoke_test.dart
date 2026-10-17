// Launches the real app wiring (main.dart) on a device: model pin, model selection, app-private
// storage. With no published or demo model installed, the app must say so and refuse to count.
// Run with flutter drive ... --no-enable-impeller on the headless emulator.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:rice_pest_app/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('with no model installed the app starts, says so, and cannot count', (tester) async {
    await app.main();
    await tester.pumpAndSettle();
    expect(find.textContaining('No model is installed'), findsOneWidget);
    final camera = tester.widget<ButtonStyleButton>(
        find.ancestor(of: find.byIcon(Icons.photo_camera), matching: find.bySubtype<ButtonStyleButton>()));
    expect(camera.onPressed, isNull);
  });
}
