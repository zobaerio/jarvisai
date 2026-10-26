import 'package:flutter_test/flutter_test.dart';
import 'package:jarvis_mobile/provider_config.dart';

void main() {
  group('ProviderConfig.normalizeBaseUrl', () {
    test('normalizes trailing slashes on HTTPS endpoint', () {
      expect(
        ProviderConfig.normalizeBaseUrl(' https://api.example.com/v1/// '),
        'https://api.example.com/v1',
      );
    });

    test('rejects plain HTTP and malformed URLs', () {
      expect(() => ProviderConfig.normalizeBaseUrl('http://api.example.com/v1'),
          throwsFormatException);
      expect(() => ProviderConfig.normalizeBaseUrl('not a URL'), throwsFormatException);
    });

    test('rejects embedded credentials, query, and fragment', () {
      for (final url in [
        'https://user:password@api.example.com/v1',
        'https://api.example.com/v1?token=secret',
        'https://api.example.com/v1#fragment',
      ]) {
        expect(() => ProviderConfig.normalizeBaseUrl(url), throwsFormatException);
      }
    });

    test('rejects localhost endpoint on phone', () {
      expect(() => ProviderConfig.normalizeBaseUrl('https://localhost:11434/v1'),
          throwsFormatException);
    });
  });

  group('ProviderConfig.validateModel', () {
    test('trims model name', () {
      expect(ProviderConfig.validateModel('  example-model  '), 'example-model');
    });

    test('rejects empty and oversized model names', () {
      expect(() => ProviderConfig.validateModel(' '), throwsFormatException);
      expect(() => ProviderConfig.validateModel('m' * 201), throwsFormatException);
    });
  });
}
