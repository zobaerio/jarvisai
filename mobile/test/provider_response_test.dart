import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:jarvis_mobile/provider_response.dart';

void main() {
  group('readBoundedResponse', () {
    test('reads a response in multiple chunks', () async {
      final result = await readBoundedResponse(Stream<List<int>>.fromIterable([
        utf8.encode('hello '),
        utf8.encode('JARVIS'),
      ]));
      expect(result, 'hello JARVIS');
    });

    test('rejects a streamed body before buffering beyond the limit', () async {
      final stream = Stream<List<int>>.fromIterable([
        List<int>.filled(5, 65),
        List<int>.filled(6, 66),
      ]);
      await expectLater(
        readBoundedResponse(stream, maxBytes: 10),
        throwsFormatException,
      );
    });

    test('rejects invalid UTF-8', () async {
      await expectLater(
        readBoundedResponse(Stream<List<int>>.value([0xC3, 0x28])),
        throwsFormatException,
      );
    });
  });

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
