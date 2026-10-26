import 'dart:convert';
import 'dart:typed_data';

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


/// Reads a streamed HTTP body while enforcing a hard byte limit before the
/// entire payload is buffered. Throws without including provider data.
Future<String> readBoundedResponse(
  Stream<List<int>> stream, {
  int maxBytes = maxProviderResponseBytes,
}) async {
  if (maxBytes < 1) {
    throw const FormatException('Response size limit is invalid.');
  }
  final builder = BytesBuilder(copy: false);
  var total = 0;
  await for (final chunk in stream) {
    total += chunk.length;
    if (total > maxBytes) {
      throw const FormatException('Provider response is too large.');
    }
    builder.add(chunk);
  }
  try {
    return utf8.decode(builder.takeBytes());
  } on FormatException {
    throw const FormatException('Provider response is not valid UTF-8.');
  }
}
