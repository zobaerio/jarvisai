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
  runApp(const OrvixMobileApp());
}

class OrvixMobileApp extends StatelessWidget {
  const OrvixMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    const accent = Color(0xFF22D3EE);
    return MaterialApp(
      title: 'ORVIX AI',
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
