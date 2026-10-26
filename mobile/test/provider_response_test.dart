import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:jarvis_mobile/provider_response.dart';

void main() {
  group('parseChatCompletion', () {
    test('extracts and trims assistant text', () {
      expect(parseChatCompletion(jsonEncode({'choices': [{'message': {'content': '  Hello from JARVIS  '}}]})), 'Hello from JARVIS');
    });
    test('rejects oversized provider response before decoding', () {
      expect(() => parseChatCompletion(' ' * (maxProviderResponseBytes + 1)), throwsFormatException);
    });
    test('rejects invalid JSON and unexpected shapes', () {
      expect(() => parseChatCompletion('{broken'), throwsFormatException);
      expect(() => parseChatCompletion('[]'), throwsFormatException);
      expect(() => parseChatCompletion('{"choices":[]}'), throwsFormatException);
      expect(() => parseChatCompletion(jsonEncode({'choices': [{'message': {'content': ''}}]})), throwsFormatException);
    });
    test('rejects oversized assistant content', () {
      expect(() => parseChatCompletion(jsonEncode({'choices': [{'message': {'content': 'x' * (maxAssistantMessageChars + 1)}}]})), throwsFormatException);
    });
  });
}
