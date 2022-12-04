#
# This file is part of LiteX.
#
# Copyright (c) 2021 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

from litex import get_data_mod
import os

from migen import *
from migen.genlib.misc import WaitTimer

from litex.soc.interconnect import axi, wishbone
from litex.soc.cores.cpu import CPU, CPU_GCC_TRIPLE_RISCV64

# Variants -----------------------------------------------------------------------------------------

# TODO: add different ISAs to cpu variants
CPU_VARIANTS = ["standard"]

# FemtoRV ------------------------------------------------------------------------------------------


class OpenPiton(CPU):
    name = "openpiton"
    human_name = "OpenPiton RISC-V 64Bit SoC"
    variants = CPU_VARIANTS
    data_width = 512
    addr_width = 64
    endianness = "little"
    gcc_triple = CPU_GCC_TRIPLE_RISCV64
    linker_output_format = "elf64-littleriscv"
    nop = "nop"
    # FIXME: is this correct?
    # io_regions = {0x00000000: 0x80000000}  # Origin, Length
    reset_address = 0x0000_0000
    io_regions           = {0x8000_0000: 0x8000_0000} # Origin, Length.
    family               = "riscv"


    # GCC Flags.
    @property
    def gcc_flags(self):
        flags = "-march=rv64imac "
        flags += "-mabi=lp64 "
        flags += "-D__openpitonrv64__ "
        return flags

    @property
    def mem_map(self):
        # Rocket reserves the first 256Mbytes for internal use, so we must change default mem_map.
        return {
            # "rom"      : 0x1000_0000,
            "main_ram" : 0x4000_0000,
            "csr"      : 0x8000_0000
        }


    def __init__(self, platform, variant="standard"):
        self.platform = platform
        self.variant = variant

        self.reset = Signal()
        # self.interrupt = Signal(32)

        # AXI bus directly connecting to OpenPiton
        self.mem_axi = mem_axi = axi.AXIInterface(
            data_width=self.data_width, address_width=self.addr_width, id_width=4)

        # Wishbone bus for the memory region in LiteX
        self.mem_wb = mem_wb = wishbone.Interface(
            data_width=self.data_width, adr_width=64-log2_int(self.data_width//8))

        # Wishbone bus for the I/O region in LiteX
        self.io_wb = io_wb = wishbone.Interface(data_width=32, adr_width=64-log2_int(32//8))

        # AXI mem bus to LiteX
        self.mem_axi_litex = mem_axi_litex = axi.AXIInterface(
            data_width=self.data_width, address_width=self.addr_width, id_width=4)

        # AXI I/O bus to LiteX
        self.io_axi_litex = io_axi_litex = axi.AXIInterface(
            data_width=self.data_width, address_width=self.addr_width, id_width=4)

        # Down converted 32 bits AXI I/O bus
        self.io_axi_down_conv = io_axi_down_conv = axi.AXIInterface(
            data_width=32, address_width=self.addr_width, id_width=4)
        
        # Peripheral buses (Connected to main SoC's bus).
        self.periph_buses = [mem_wb, io_wb]
        # Memory buses (Connected directly to LiteDRAM).
        self.memory_buses = []

        wait_timer = WaitTimer(5000)
        self.submodules += wait_timer
        self.comb += wait_timer.wait.eq(1)

        # OpenPiton RISCV 64 Instance.
        # -----------------
        self.cpu_params = dict(
            # Parameters.

            # Clk / Rst.
            i_sys_clk=ClockSignal("sys"),
            i_sys_rst_n=wait_timer.done,  # Active Low.

            # Additional clocks
            i_core_ref_clk=ClockSignal("sys"),
            i_io_clk=ClockSignal("sys"),

            i_mc_clk=ClockSignal("sys"),

            o_m_axi_awid=mem_axi.aw.id,
            o_m_axi_awaddr=mem_axi.aw.addr,
            o_m_axi_awlen=mem_axi.aw.len,
            o_m_axi_awsize=mem_axi.aw.size,
            o_m_axi_awburst=mem_axi.aw.burst,
            o_m_axi_awlock=mem_axi.aw.lock,
            o_m_axi_awcache=mem_axi.aw.cache,
            o_m_axi_awprot=mem_axi.aw.prot,
            o_m_axi_awqos=mem_axi.aw.qos,
            # o_m_axi_awregion=mem_axi.aw.region,
            #o_m_axi_awuser=mem_axi.aw.user,
            o_m_axi_awvalid=mem_axi.aw.valid,
            i_m_axi_awready=mem_axi.aw.ready,

            o_m_axi_wid=mem_axi.w.id,
            o_m_axi_wdata=mem_axi.w.data,
            o_m_axi_wstrb=mem_axi.w.strb,
            o_m_axi_wlast=mem_axi.w.last,
            #o_m_axi_wuser=mem_axi.w.user,
            o_m_axi_wvalid=mem_axi.w.valid,
            i_m_axi_wready=mem_axi.w.ready,

            o_m_axi_arid=mem_axi.ar.id,
            o_m_axi_araddr=mem_axi.ar.addr,
            o_m_axi_arlen=mem_axi.ar.len,
            o_m_axi_arsize=mem_axi.ar.size,
            o_m_axi_arburst=mem_axi.ar.burst,
            o_m_axi_arlock=mem_axi.ar.lock,
            o_m_axi_arcache=mem_axi.ar.cache,
            o_m_axi_arprot=mem_axi.ar.prot,
            o_m_axi_arqos=mem_axi.ar.qos,
#            o_m_axi_arregion=mem_axi.ar.region,
            #o_m_axi_aruser=mem_axi.ar.user,
            o_m_axi_arvalid=mem_axi.ar.valid,
            i_m_axi_arready=mem_axi.ar.ready,

            i_m_axi_rid=mem_axi.r.id,
            i_m_axi_rdata=mem_axi.r.data,
            i_m_axi_rresp=mem_axi.r.resp,
            i_m_axi_rlast=mem_axi.r.last,
            #i_m_axi_ruser=mem_axi.r.user,
            i_m_axi_rvalid=mem_axi.r.valid,
            o_m_axi_rready=mem_axi.r.ready,

            i_m_axi_bid=mem_axi.b.id,
            i_m_axi_bresp=mem_axi.b.resp,
            #i_m_axi_buser=mem_axi.b.user,
            i_m_axi_bvalid=mem_axi.b.valid,
            o_m_axi_bready=mem_axi.b.ready,

            # TODO: add ddr ready
            i_ddr_ready=1,
            i_ext_irq=0,
            i_ext_irq_trigger=0,

        )

        # OpenPiton to LiteX adapter structure
        # OpenPiton AXI iface <-> | MEM | <-> MEM AXI LiteX  <Convert> 512b WB
        #                         | AXI | <-> I/O AXI LiteX <DownCast> 32b AXI <-> 32b WB
        # WBs at the end are all adapted into 512b WBs
        # No. Increasing data width is counter productive.
        # Over-reading the CSRs are not desirable.

        # OpenPiton to LiteX, AXI Decoder
        op2litex_decoder = ResetInserter()(
            axi.AXIDecoder(mem_axi, [
                (lambda addr: ~addr[31-log2_int(mem_axi.data_width//8)], mem_axi_litex),
                (lambda addr: addr[31-log2_int(mem_axi.data_width//8)], io_axi_litex)]))
        self.comb += op2litex_decoder.reset.eq(ResetSignal() | self.reset)
        self.submodules += op2litex_decoder

        # Memory region path
        mem_bus_a2w = ResetInserter()(axi.AXI2Wishbone(mem_axi_litex, mem_wb, base_address=0))
        # Note: Must be reset with the CPU.
        self.comb += mem_bus_a2w.reset.eq(ResetSignal() | self.reset)
        self.submodules += mem_bus_a2w

        # I/O region path
        #
        # Down cast 512b I/O bus to 32b
        # Actually better than any other available intermediate logics
        # In addition, duplicate the returned value to fill the 512b data width of OpenPiton
        # Then we can avoid head-butting the data processing that the NOC-AXI bridge does
        self.comb += [
            io_axi_litex.connect(io_axi_down_conv),
            io_axi_litex.r.data[32:].eq(Replicate(io_axi_down_conv.r.data, 512//32))
        ]

        io_bus_a2w = ResetInserter()(axi.AXI2Wishbone(io_axi_down_conv, io_wb, base_address=0))
        # Note: Must be reset with the CPU.
        self.comb += io_bus_a2w.reset.eq(ResetSignal() | self.reset)
        self.submodules += io_bus_a2w

        # Add Verilog sources.
        # --------------------
        self.add_sources(platform)

    @staticmethod
    def add_sources(platform):
        if not os.path.exists("generated.v"):
            os.system("cp ~/research/openpiton/build/generated.v .")
        platform.add_source("generated.sv")

    def do_finalize(self):
        assert hasattr(self, "reset_address")
        self.specials += Instance("system", **self.cpu_params)
