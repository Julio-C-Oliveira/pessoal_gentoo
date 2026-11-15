#!/usr/bin/env python3
"""
Testes unitários para o utilitário emerge-progress.
Valida o parser para Ninja, CMake, Cargo, GNU Make/Autotools e emerge.log.
"""

import os
import sys
import tempfile
import unittest
import shutil

# Adiciona o diretório scripts ao path para importar as classes de emerge-progress
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Como o script não tem extensão .py, importamos via importlib
from importlib.machinery import SourceFileLoader
import importlib.util

script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "emerge-progress")
loader = SourceFileLoader("emerge_progress", script_path)
spec = importlib.util.spec_from_loader("emerge_progress", loader)
ep = importlib.util.module_from_spec(spec)
loader.exec_module(ep)


class TestEmergeProgressParsers(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.portage_tmp = os.path.join(self.test_dir, "portage")
        self.emerge_log = os.path.join(self.test_dir, "emerge.log")
        os.makedirs(self.portage_tmp, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_ninja_parser(self):
        """Testa captura de etapas [X/Y] do Ninja/Meson."""
        parser = ep.BuildLogParser(portage_tmp_dir=self.portage_tmp)
        chunk = """
[1/100] Compiling C object src/foo.o
[25/100] Compiling CXX object src/bar.cpp.o
[ 50/100 ] Linking target bin/app
"""
        parser._process_chunk(chunk)
        self.assertEqual(parser.build_system, "Ninja")
        self.assertEqual(parser.current_step, 50)
        self.assertEqual(parser.total_steps, 100)
        self.assertEqual(parser.percentage, 50.0)
        self.assertEqual(parser.current_target, "Linking target bin/app")

    def test_cmake_parser(self):
        """Testa captura de porcentagem [X%] do CMake."""
        parser = ep.BuildLogParser(portage_tmp_dir=self.portage_tmp)
        chunk = """
[ 10%] Building C object CMakeFiles/app.dir/main.c.o
[ 75%] Building C object CMakeFiles/app.dir/util.c.o
"""
        parser._process_chunk(chunk)
        self.assertEqual(parser.build_system, "CMake")
        self.assertEqual(parser.percentage, 75.0)
        self.assertIn("util.c.o", parser.current_target)

    def test_cargo_parser(self):
        """Testa captura de compilação de crates Cargo (Rust)."""
        parser = ep.BuildLogParser(portage_tmp_dir=self.portage_tmp)
        chunk = """
   Compiling libc v0.2.147
   Compiling syn v2.0.48
   Compiling ripgrep v14.1.0 (15/30)
"""
        parser._process_chunk(chunk)
        self.assertEqual(parser.build_system, "Cargo")
        self.assertEqual(parser.current_step, 15)
        self.assertEqual(parser.total_steps, 30)
        self.assertEqual(parser.percentage, 50.0)

    def test_make_autotools_parser(self):
        """Testa captura de compilação clássica Make / GCC (como na foto do usuário: libavfilter/f_metadata.o)."""
        parser = ep.BuildLogParser(portage_tmp_dir=self.portage_tmp)
        # Linha exata vista na foto do usuário:
        chunk = """
x86_64-pc-linux-gnu-gcc -I. -Isrc/ -D_ISOC11_SOURCE -O2 -pipe -Wempty-body -c -o libavfilter/f_metadata.o src/libavfilter/f_metadata.c
x86_64-pc-linux-gnu-gcc -I. -Isrc/ -D_ISOC11_SOURCE -O2 -pipe -c -o libavfilter/f_loop.o src/libavfilter/f_loop.c
"""
        parser._process_chunk(chunk)
        self.assertEqual(parser.build_system, "Make/Autotools")
        self.assertEqual(parser.objects_compiled, 2)
        self.assertEqual(parser.current_target, "f_loop.o")

    def test_make_silent_rules(self):
        """Testa compilação com Kbuild ou Silent Rules (CC foo.o)."""
        parser = ep.BuildLogParser(portage_tmp_dir=self.portage_tmp)
        chunk = """
  CC      kernel/fork.o
  CC      kernel/sched/core.o
  LD      kernel/built-in.a
"""
        parser._process_chunk(chunk)
        self.assertEqual(parser.build_system, "Make/Autotools")
        self.assertEqual(parser.objects_compiled, 3)

    def test_emerge_log_queue_and_history(self):
        """Testa extração de fila e histórico de tempo do emerge.log."""
        # Cria um emerge.log simulado
        # 1. Compilação anterior de ffmpeg que durou 120s
        # 2. Início do emerge atual: pacote 2 de 5 sendo compilado
        log_content = """1700000000: Started emerge on: Nov 15, 2026 10:00:00
1700000010:  *** emerge (1 of 1) media-video/ffmpeg-6.0 to /
1700000015:  === (1 of 1) Cleaning (media-video/ffmpeg-6.0::gentoo)
1700000020:  === (1 of 1) Compiling/Packaging (media-video/ffmpeg-6.0::gentoo)
1700000140:  === (1 of 1) Merging (media-video/ffmpeg-6.0::gentoo)
1700000150:  === (1 of 1) Completed installation (media-video/ffmpeg-6.0::gentoo)
1700000160:  *** Finished. Cleaning up...
1700000200: Started emerge on: Nov 15, 2026 12:00:00
1700000205:  *** emerge (2 of 5) media-video/ffmpeg-6.1 to /
1700000210:  === (2 of 5) Compiling/Packaging (media-video/ffmpeg-6.1::gentoo)
"""
        with open(self.emerge_log, "w") as f:
            f.write(log_content)

        watcher = ep.EmergeLogWatcher(log_path=self.emerge_log)
        state = watcher.get_current_state()

        self.assertTrue(state["active"])
        self.assertEqual(state["current_idx"], 2)
        self.assertEqual(state["total_pkgs"], 5)
        self.assertEqual(state["package"], "media-video/ffmpeg-6.1")
        self.assertEqual(state["phase"], "Compiling/Packaging")

        # Verifica cálculo de histórico
        hist_time = watcher.get_historical_compile_time("media-video/ffmpeg-6.1")
        # Deve encontrar a compilação anterior (1700000140 - 1700000020 = 120.0 segundos)
        self.assertIsNotNone(hist_time)
        self.assertEqual(hist_time, 120.0)

    def test_progress_bar_drawing(self):
        """Testa desenho da barra de progresso."""
        colors = ep.Colors(enabled=False)
        bar_50 = ep.draw_progress_bar(50.0, width=20, color=colors)
        self.assertIn("50.0%", bar_50)
        self.assertIn("█" * 10, bar_50)

        bar_none = ep.draw_progress_bar(None, width=20, color=colors)
        self.assertIn("---%", bar_none)


if __name__ == "__main__":
    unittest.main()
