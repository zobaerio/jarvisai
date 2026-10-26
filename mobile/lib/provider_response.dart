import 'dart:convert';

/// Strict parsing for OpenAI-compatible chat completion responses.
const int maxProviderResponseBytes = 1024 * 1024;
const int maxAssistantMessageChars = 20000;

/// Parses one assistant message from a bounded JSON response.
///
/// Throws [FormatException] for malformed, oversized, empty, or unsupported
/// provider responses. The raw response is never included in the exception.
String parseChatCompletion(String body) {
  if (body.length > maxProviderResponseBytes) {
    throw const FormatException('Provider response is too large.');
  }
  final decoded = jsonDecode(body);
  if (decoded is! Map) {
    throw const FormatException('Provider response must be a JSON object.');
  }
  final choices = decoded['choices'];
  if (choices is! List || choices.isEmpty || choices.first is! Map) {
    throw const FormatException('Provider response has no chat completion.');
  }
  final message = choices.first['message'];
  final content = message is Map ? message['content'] : null;
  if (content is! String || content.trim().isEmpty || content.length > maxAssistantMessageChars) {
    throw const FormatException('Provider response has no supported assistant text.');
  }
  return content.trim();
}
