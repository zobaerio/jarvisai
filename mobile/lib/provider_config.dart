import 'package:flutter/foundation.dart';

@immutable
class ProviderConfig {
  const ProviderConfig({required this.baseUrl, required this.model});

  final String baseUrl;
  final String model;

  static String normalizeBaseUrl(String input) {
    final value = input.trim().replaceFirst(RegExp(r'/+$'), '');
    final uri = Uri.tryParse(value);
    if (uri == null ||
        uri.scheme.toLowerCase() != 'https' ||
        uri.host.isEmpty ||
        uri.userInfo.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment) {
      throw const FormatException(
        'Use a valid HTTPS API base URL without embedded credentials, query, or fragment.',
      );
    }
    if (uri.host.toLowerCase() == 'localhost' ||
        uri.host == '127.0.0.1' ||
        uri.host == '::1') {
      throw const FormatException(
        'A phone cannot use the computer localhost address. Use a reachable HTTPS endpoint.',
      );
    }
    return value;
  }

  static String validateModel(String input) {
    final value = input.trim();
    if (value.isEmpty || value.length > 200 || value.contains(RegExp(r'[\r\n\x00-\x1f]'))) {
      throw const FormatException('Enter a valid model name.');
    }
    return value;
  }
}
