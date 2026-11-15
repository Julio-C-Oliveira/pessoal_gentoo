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

    def test_real_emerge_log_format_and_parallel_jobs(self):
        """Testa o formato real do emerge.log (>>> emerge e ::: completed emerge) com jobs paralelos."""
        log_content = """1700001000: Started emerge on: Nov 15, 2026 13:00:00
1700001005:  >>> emerge (1 of 10) dev-libs/boehm-gc-8.2.12 to /
1700001006:  >>> emerge (2 of 10) dev-libs/libconfig-1.8.2 to /
1700001010:  === (1 of 10) Compiling/Packaging (dev-libs/boehm-gc-8.2.12::gentoo)
1700001011:  === (2 of 10) Compiling/Packaging (dev-libs/libconfig-1.8.2::gentoo)
1700001025:  ::: completed emerge (1 of 10) dev-libs/boehm-gc-8.2.12 to /
1700001026:  >>> emerge (3 of 10) x11-libs/libxcb-1.17.0 to /
"""
        with open(self.emerge_log, "w") as f:
            f.write(log_content)

        watcher = ep.EmergeLogWatcher(log_path=self.emerge_log)
        state = watcher.get_current_state()

        self.assertTrue(state["active"])
        self.assertEqual(state["total_pkgs"], 10)
        self.assertEqual(state["completed_count"], 1)
        self.assertIsNotNone(state["last_completed"])
        self.assertEqual(state["last_completed"]["package"], "dev-libs/boehm-gc-8.2.12")
        self.assertEqual(state["last_completed"]["duration"], 20.0)
        self.assertIn("dev-libs/libconfig-1.8.2", state["active_packages"])
        self.assertIn("x11-libs/libxcb-1.17.0", state["active_packages"])
        self.assertNotIn("dev-libs/boehm-gc-8.2.12", state["active_packages"])
        # Pacote recém-enfileirado sem fase === explícita não deve ficar com fase vazia
        self.assertEqual(state["active_packages"]["x11-libs/libxcb-1.17.0"]["phase"], "Iniciando")

    def test_configure_and_source_estimation(self):
        """Testa detecção de ./configure, contagem de fontes em work/ e deduplicação libtool."""
        pkg_base = os.path.join(self.portage_tmp, "dev-libs", "libconfig-1.8.2")
        work_src = os.path.join(pkg_base, "work", "libconfig-1.8.2", "lib")
        work_tests = os.path.join(pkg_base, "work", "libconfig-1.8.2", "tests")
        temp_dir = os.path.join(pkg_base, "temp")
        os.makedirs(work_src, exist_ok=True)
        os.makedirs(work_tests, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

        # 4 fontes reais em lib/ + arquivos ignorados (tests/ e conftest.c)
        for fname in ("libconfig.c", "scanner.c", "grammar.c", "libconfigcpp.c++"):
            with open(os.path.join(work_src, fname), "w") as f:
                f.write("/* src */\n")
        with open(os.path.join(work_src, "conftest.c"), "w") as f:
            f.write("/* ignore */\n")
        with open(os.path.join(work_tests, "unit_test.c"), "w") as f:
            f.write("/* ignore tests */\n")

        build_log = os.path.join(temp_dir, "build.log")
        with open(build_log, "w") as f:
            f.write("checking for x86_64-pc-linux-gnu-gcc... x86_64-pc-linux-gnu-gcc\n")
            f.write("checking whether the C compiler works... yes\n")

        parser = ep.BuildLogParser(portage_tmp_dir=self.portage_tmp)
        parser.update_from_file(build_log)
        self.assertEqual(parser.build_system, "./configure")
        self.assertEqual(parser.configure_checks, 2)
        self.assertIsNone(parser.percentage)

        # Agora simula compilação com saídas duplicadas do libtool (PIC + non-PIC + wrapper)
        with open(build_log, "a") as f:
            f.write(
                "/bin/sh ../libtool --tag=CXX --mode=compile x86_64-pc-linux-gnu-g++ -c -o libconfig___la-libconfigcpp.lo libconfigcpp.c++\n"
            )
            f.write(
                "libtool: compile:  x86_64-pc-linux-gnu-g++ -c libconfigcpp.c++ -fPIC -DPIC -o .libs/libconfig___la-libconfigcpp.o\n"
            )
            f.write(
                "libtool: compile:  x86_64-pc-linux-gnu-g++ -c libconfigcpp.c++ -o libconfig___la-libconfigcpp.o >/dev/null 2>&1\n"
            )
            f.write(
                "libtool: compile:  x86_64-pc-linux-gnu-gcc -c libconfig.c -fPIC -DPIC -o .libs/libconfig_la-libconfig.o\n"
            )

        parser.update_from_file(build_log)
        self.assertEqual(parser.build_system, "Make/Autotools")
        self.assertEqual(parser.objects_compiled, 2)
        self.assertEqual(parser.total_source_files, 4)
        self.assertTrue(parser.is_estimated)
        self.assertEqual(parser.percentage, 50.0)

    def test_multi_build_monitor_and_general_display(self):
        """Testa monitoramento simultâneo (--jobs=2) e renderização do Progresso Geral sem overflow de linha."""
        log_content = """1700002000: Started emerge on: Nov 15, 2026 13:30:00
1700002005:  >>> emerge (1 of 4) dev-libs/first-1.0 to /
1700002015:  ::: completed emerge (1 of 4) dev-libs/first-1.0 to /
1700002020:  >>> emerge (2 of 4) dev-libs/boehm-gc-8.2.12 to /
1700002021:  >>> emerge (3 of 4) dev-libs/libconfig-1.8.2 to /
1700002022:  === (2 of 4) Compiling/Packaging (dev-libs/boehm-gc-8.2.12::gentoo)
1700002023:  === (3 of 4) Compiling/Packaging (dev-libs/libconfig-1.8.2::gentoo)
"""
        with open(self.emerge_log, "w") as f:
            f.write(log_content)

        # Cria dois build.log simultâneos
        for pkg, content in (
            ("dev-libs/boehm-gc-8.2.12", "[10/20] Compiling C object mark.o\n"),
            ("dev-libs/libconfig-1.8.2", "[ 50%] Building C object very/long/path/inside/build/tree/libconfig_extremely_long_object_filename.c.o\n"),
        ):
            cat, name = pkg.split("/")
            tdir = os.path.join(self.portage_tmp, cat, name, "temp")
            os.makedirs(tdir, exist_ok=True)
            with open(os.path.join(tdir, "build.log"), "w") as bf:
                bf.write(content)

        watcher = ep.EmergeLogWatcher(log_path=self.emerge_log)
        state = watcher.get_current_state()
        monitor = ep.MultiBuildMonitor(portage_tmp_dir=self.portage_tmp)
        parsers = monitor.update_all(state, watcher)

        self.assertEqual(len(parsers), 2)
        pkgs_found = {p.package_name for p in parsers}
        self.assertEqual(pkgs_found, {"dev-libs/boehm-gc-8.2.12", "dev-libs/libconfig-1.8.2"})

        # Atualiza novamente e verifica que os contadores não zeram nem alternam
        parsers2 = monitor.update_all(state, watcher)
        self.assertEqual(len(parsers2), 2)
        for p in parsers2:
            self.assertEqual(p.percentage, 50.0)

        colors = ep.Colors(enabled=False)
        term_w = 80
        output = ep.render_multi_display(
            emerge_state=state,
            parsers=parsers2,
            colors=colors,
            single_line=False,
            term_width=term_w,
            system_metrics={"load_1m": 1.5, "load_5m": 1.2, "ram_used_gb": 3.2, "ram_total_gb": 8.0, "ram_pct": 40.0},
        )

        self.assertIn("Progresso Geral da Fila", output)
        self.assertIn("1/4 concluídos (2 ativos)", output)
        self.assertIn("50.0%", output)  # (1 + 0.5 + 0.5) / 4 = 50.0%
        self.assertIn("Último concluído: dev-libs/first-1.0", output)
        self.assertIn("dev-libs/boehm-gc-8.2.12", output)
        self.assertIn("dev-libs/libconfig-1.8.2", output)
        self.assertNotIn("[]", output)

        for line in output.split("\n"):
            self.assertLess(ep.visible_len(line), term_w, f"Linha excedeu largura: {line}")

        # Verifica truncate_ansi preservando limite de largura visível
        ansi_str = "\033[36m" + ("A" * 100) + "\033[0m"
        truncated = ep.truncate_ansi(ansi_str, 30)
        self.assertLessEqual(ep.visible_len(truncated), 30)
        self.assertTrue(truncated.endswith("\033[0m"))

        # Verifica modo --once
        once_out = ep.render_multi_display(
            emerge_state=state,
            parsers=parsers2,
            colors=colors,
            single_line=True,
            term_width=120,
        )
        self.assertIn("Fila: 1/4 (50.0%", once_out)
        self.assertLess(ep.visible_len(once_out), 120)


if __name__ == "__main__":
    unittest.main()
