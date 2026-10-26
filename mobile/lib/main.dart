import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'provider_config.dart';
import 'provider_response.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const JarvisMobileApp());
}

class JarvisMobileApp extends StatelessWidget {
  const JarvisMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    const accent = Color(0xFF22D3EE);
    return MaterialApp(
      title: 'J.A.R.V.I.S',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF08111F),
        colorScheme: ColorScheme.fromSeed(
          seedColor: accent,
          brightness: Brightness.dark,
          surface: const Color(0xFF111D30),
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF08111F),
          foregroundColor: Colors.white,
          centerTitle: false,
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: const Color(0xFF142238),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: BorderSide.none,
          ),
        ),
        useMaterial3: true,
      ),
      home: const ChatScreen(),
    );
  }
}

class ChatMessage {
  const ChatMessage({required this.role, required this.text});
  final String role;
  final String text;
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  static const _storage = FlutterSecureStorage();
  final _input = TextEditingController();
  final _scroll = ScrollController();
  final List<ChatMessage> _messages = [];
  String _baseUrl = 'https://api.openai.com/v1';
  String _model = '';
  String _apiKey = '';
  bool _busy = false;
  bool _loading = true;
  String? _status;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _loadSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final key = await _storage.read(key: 'provider_api_key');
      if (!mounted) return;
      setState(() {
        _baseUrl = prefs.getString('provider_base_url') ?? _baseUrl;
        _model = prefs.getString('provider_model') ?? '';
        _apiKey = key ?? '';
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _status = 'Settings could not be loaded. Reopen settings and try again.';
      });
    }
  }

  Future<void> _openSettings() async {
    final base = TextEditingController(text: _baseUrl);
    final model = TextEditingController(text: _model);
    final key = TextEditingController(text: _apiKey);
    bool saving = false;
    String? error;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF101C2F),
      builder: (sheetContext) => StatefulBuilder(
        builder: (context, setSheetState) => Padding(
          padding: EdgeInsets.fromLTRB(
            20, 20, 20, MediaQuery.of(context).viewInsets.bottom + 24,
          ),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text('AI Provider Settings',
                    style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                const Text(
                  'Use an OpenAI-compatible HTTPS endpoint. Your API key is stored in the device secure-storage facility.',
                  style: TextStyle(color: Colors.white70),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: base,
                  keyboardType: TextInputType.url,
                  autocorrect: false,
                  decoration: const InputDecoration(labelText: 'API base URL'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: model,
                  autocorrect: false,
                  decoration: const InputDecoration(labelText: 'Model name'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: key,
                  obscureText: true,
                  autocorrect: false,
                  enableSuggestions: false,
                  decoration: const InputDecoration(labelText: 'API key'),
                ),
                if (error != null) ...[
                  const SizedBox(height: 12),
                  Text(error!, style: const TextStyle(color: Colors.orangeAccent)),
                ],
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: saving
                      ? null
                      : () async {
                          setSheetState(() {
                            saving = true;
                            error = null;
                          });
                          try {
                            final safeUrl = ProviderConfig.normalizeBaseUrl(base.text);
                            final safeModel = ProviderConfig.validateModel(model.text);
                            if (key.text.trim().isEmpty) {
                              throw const FormatException('Enter an API key.');
                            }
                            final prefs = await SharedPreferences.getInstance();
                            await prefs.setString('provider_base_url', safeUrl);
                            await prefs.setString('provider_model', safeModel);
                            await _storage.write(
                              key: 'provider_api_key',
                              value: key.text.trim(),
                            );
                            if (!mounted) return;
                            setState(() {
                              _baseUrl = safeUrl;
                              _model = safeModel;
                              _apiKey = key.text.trim();
                              _status = 'Provider settings saved securely.';
                            });
                            if (sheetContext.mounted) Navigator.pop(sheetContext);
                          } on FormatException catch (e) {
                            setSheetState(() => error = e.message);
                          } catch (_) {
                            setSheetState(() => error =
                                'Settings could not be saved. Check device storage and try again.');
                          } finally {
                            if (sheetContext.mounted) {
                              setSheetState(() => saving = false);
                            }
                          }
                        },
                  child: Text(saving ? 'Saving…' : 'Save Settings'),
                ),
                TextButton(
                  onPressed: () => Navigator.pop(sheetContext),
                  child: const Text('Cancel'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
    base.dispose();
    model.dispose();
    key.dispose();
  }

  Future<void> _testConnection() async {
    if (_apiKey.isEmpty || _model.isEmpty) {
      setState(() => _status = 'Open settings and configure the API key and model first.');
      return;
    }
    setState(() {
      _busy = true;
      _status = 'Checking provider…';
    });
    try {
      final uri = Uri.parse('$_baseUrl/models');
      final response = await http.get(
        uri,
        headers: {'Authorization': 'Bearer $_apiKey', 'Accept': 'application/json'},
      ).timeout(const Duration(seconds: 15));
      if (!mounted) return;
      setState(() => _status = response.statusCode >= 200 && response.statusCode < 300
          ? 'Provider endpoint is reachable. A chat request has not been sent.'
          : 'Provider check failed (HTTP ${response.statusCode}). Check endpoint, key, and provider permissions.');
    } catch (_) {
      if (mounted) setState(() => _status =
          'Could not reach the provider. Check internet access, HTTPS endpoint, and model settings.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _sendMessage() async {
    final text = _input.text.trim();
    if (text.isEmpty || _busy) return;
    if (_apiKey.isEmpty || _model.isEmpty) {
      setState(() => _status = 'Configure an AI provider before sending a message.');
      await _openSettings();
      return;
    }
    setState(() {
      _messages.add(ChatMessage(role: 'user', text: text));
      _input.clear();
      _busy = true;
      _status = null;
    });
    _scrollToBottom();
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/chat/completions'),
        headers: {
          'Authorization': 'Bearer $_apiKey',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: jsonEncode({
          'model': _model,
          'messages': [
            {
              'role': 'system',
              'content':
                  'You are J.A.R.V.I.S, a helpful assistant. Be honest about capabilities. This mobile client cannot control the phone or the user’s Windows desktop. Never claim to have performed device actions unless a supported tool actually did so.',
            },
            ..._messages.skip(_messages.length > 20 ? _messages.length - 20 : 0).map(
              (m) => {'role': m.role, 'content': m.text},
            ),
          ],
          'temperature': 0.4,
        }),
      ).timeout(const Duration(seconds: 45));
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw _ProviderException('Provider returned HTTP ${response.statusCode}. Check the model, API key, and endpoint.');
      }
      final content = parseChatCompletion(response.body);
      if (!mounted) return;
      setState(() {
        _messages.add(ChatMessage(role: 'assistant', text: content));
      });
    } on _ProviderException catch (e) {
      if (mounted) setState(() => _status = e.message);
    } on FormatException {
      if (mounted) setState(() => _status = 'Provider returned an invalid response. Check the endpoint and model.');
    } catch (_) {
      if (mounted) setState(() => _status =
          'Message failed. Check your internet connection and provider settings, then try again.');
    } finally {
      if (mounted) {
        setState(() => _busy = false);
        _scrollToBottom();
      }
    }
  }


  Future<void> _clearConversation() async {
    if (_messages.isEmpty || _busy) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Clear this conversation?'),
        content: const Text('Messages are only kept in memory. Clearing removes the current conversation from this screen.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('Clear chat')),
        ],
      ),
    );
    if (confirmed == true && mounted) {
      setState(() {
        _messages.clear();
        _status = 'Conversation cleared.';
      });
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('J.A.R.V.I.S', style: TextStyle(fontWeight: FontWeight.w800)),
            Text('MOBILE AI ASSISTANT',
                style: TextStyle(fontSize: 10, letterSpacing: 1.5, color: Color(0xFF22D3EE))),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Test provider connection',
            onPressed: _busy ? null : _testConnection,
            icon: const Icon(Icons.wifi_tethering),
          ),
          IconButton(
            tooltip: 'Clear conversation',
            onPressed: _messages.isEmpty || _busy ? null : _clearConversation,
            icon: const Icon(Icons.delete_outline),
          ),
          IconButton(
            tooltip: 'AI provider settings',
            onPressed: _busy ? null : _openSettings,
            icon: const Icon(Icons.tune),
          ),
        ],
      ),
      body: SafeArea(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : Column(
                children: [
                  Container(
                    width: double.infinity,
                    margin: const EdgeInsets.fromLTRB(16, 8, 16, 8),
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: const Color(0xFF10283A),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: const Color(0xFF1D5264)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.shield_outlined, color: Color(0xFF22D3EE)),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            _model.isEmpty
                                ? 'Set up your AI provider to start chatting.'
                                : 'Model: $_model · Chat history stays in this screen only.',
                            style: const TextStyle(fontSize: 12, color: Colors.white70),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: _messages.isEmpty
                        ? const Center(
                            child: Padding(
                              padding: EdgeInsets.all(28),
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.auto_awesome, size: 48, color: Color(0xFF22D3EE)),
                                  SizedBox(height: 16),
                                  Text('How can I help?',
                                      style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
                                  SizedBox(height: 8),
                                  Text('Ask a question, plan your work, or get help with a task.',
                                      textAlign: TextAlign.center,
                                      style: TextStyle(color: Colors.white60)),
                                ],
                              ),
                            ),
                          )
                        : ListView.builder(
                            controller: _scroll,
                            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                            itemCount: _messages.length,
                            itemBuilder: (context, index) {
                              final message = _messages[index];
                              final isUser = message.role == 'user';
                              return Align(
                                alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                                child: Container(
                                  constraints: BoxConstraints(
                                    maxWidth: MediaQuery.of(context).size.width * 0.84,
                                  ),
                                  margin: const EdgeInsets.symmetric(vertical: 6),
                                  padding: const EdgeInsets.all(14),
                                  decoration: BoxDecoration(
                                    color: isUser
                                        ? const Color(0xFF12465A)
                                        : const Color(0xFF15243A),
                                    borderRadius: BorderRadius.circular(16),
                                  ),
                                  child: SelectableText(message.text),
                                ),
                              );
                            },
                          ),
                  ),
                  if (_status != null)
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                      child: Text(_status!,
                          style: const TextStyle(color: Colors.orangeAccent, fontSize: 12)),
                    ),
                  if (_busy) const LinearProgressIndicator(minHeight: 2),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _input,
                            minLines: 1,
                            maxLines: 5,
                            maxLength: 4000,
                            maxLengthEnforcement: MaxLengthEnforcement.enforced,
                            textInputAction: TextInputAction.send,
                            onSubmitted: (_) => _sendMessage(),
                            decoration: const InputDecoration(
                              hintText: 'Message J.A.R.V.I.S…',
                              contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        IconButton.filled(
                          onPressed: _busy ? null : _sendMessage,
                          icon: const Icon(Icons.arrow_upward),
                          style: IconButton.styleFrom(
                            backgroundColor: const Color(0xFF22D3EE),
                            foregroundColor: const Color(0xFF08111F),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}

class _ProviderException implements Exception {
  const _ProviderException(this.message);
  final String message;
}
