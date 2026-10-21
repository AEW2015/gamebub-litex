########################################
# Metadata
########################################
# Set user ID to identify as Game Bub revision 4
set_property BITSTREAM.CONFIG.USERID 0xB0100004 [current_design]

########################################
# Clocking
########################################
# External 50 MHz input clock
set_property -dict { PACKAGE_PIN P17     IOSTANDARD LVCMOS33 } [get_ports { clk_50mhz }];

########################################
# Cartridge Slot
########################################
# Cartridge Bank 0: A16 to A23
set_property -dict { PACKAGE_PIN A16    IOSTANDARD LVCMOS33 } [get_ports { cart_bank0[0] }];
set_property -dict { PACKAGE_PIN B16    IOSTANDARD LVCMOS33 } [get_ports { cart_bank0[1] }];
set_property -dict { PACKAGE_PIN D12    IOSTANDARD LVCMOS33 } [get_ports { cart_bank0[2] }];
set_property -dict { PACKAGE_PIN C12    IOSTANDARD LVCMOS33 } [get_ports { cart_bank0[3] }];
set_property -dict { PACKAGE_PIN D13    IOSTANDARD LVCMOS33 } [get_ports { cart_bank0[4] }];
set_property -dict { PACKAGE_PIN F13    IOSTANDARD LVCMOS33 } [get_ports { cart_bank0[5] }];
set_property -dict { PACKAGE_PIN C14    IOSTANDARD LVCMOS33 } [get_ports { cart_bank0[6] }];
set_property -dict { PACKAGE_PIN D14    IOSTANDARD LVCMOS33 } [get_ports { cart_bank0[7] }];

# Cartridge Bank 1: AD8 to AD15
set_property -dict { PACKAGE_PIN B11    IOSTANDARD LVCMOS33 } [get_ports { cart_bank1[0] }];
set_property -dict { PACKAGE_PIN B12    IOSTANDARD LVCMOS33 } [get_ports { cart_bank1[1] }];
set_property -dict { PACKAGE_PIN A13    IOSTANDARD LVCMOS33 } [get_ports { cart_bank1[2] }];
set_property -dict { PACKAGE_PIN B13    IOSTANDARD LVCMOS33 } [get_ports { cart_bank1[3] }];
set_property -dict { PACKAGE_PIN A14    IOSTANDARD LVCMOS33 } [get_ports { cart_bank1[4] }];
set_property -dict { PACKAGE_PIN B14    IOSTANDARD LVCMOS33 } [get_ports { cart_bank1[5] }];
set_property -dict { PACKAGE_PIN A15    IOSTANDARD LVCMOS33 } [get_ports { cart_bank1[6] }];
set_property -dict { PACKAGE_PIN C15    IOSTANDARD LVCMOS33 } [get_ports { cart_bank1[7] }];

# Cartridge Bank 2: AD0 to AD7
set_property -dict { PACKAGE_PIN D5     IOSTANDARD LVCMOS33 } [get_ports { cart_bank2[0] }];
set_property -dict { PACKAGE_PIN C5     IOSTANDARD LVCMOS33 } [get_ports { cart_bank2[1] }];
set_property -dict { PACKAGE_PIN C6     IOSTANDARD LVCMOS33 } [get_ports { cart_bank2[2] }];
set_property -dict { PACKAGE_PIN D7     IOSTANDARD LVCMOS33 } [get_ports { cart_bank2[3] }];
set_property -dict { PACKAGE_PIN C7     IOSTANDARD LVCMOS33 } [get_ports { cart_bank2[4] }];
set_property -dict { PACKAGE_PIN D8     IOSTANDARD LVCMOS33 } [get_ports { cart_bank2[5] }];
set_property -dict { PACKAGE_PIN D4     IOSTANDARD LVCMOS33 } [get_ports { cart_bank2[6] }];
set_property -dict { PACKAGE_PIN E5     IOSTANDARD LVCMOS33 } [get_ports { cart_bank2[7] }];

# Cartridge Bank 3: 0: nCS1, 1: nRD, 2: nWR, 3: PHI
set_property -dict { PACKAGE_PIN C4     IOSTANDARD LVCMOS33 } [get_ports { cart_bank3[0] }];
set_property -dict { PACKAGE_PIN B7     IOSTANDARD LVCMOS33 } [get_ports { cart_bank3[1] }];
set_property -dict { PACKAGE_PIN A6     IOSTANDARD LVCMOS33 } [get_ports { cart_bank3[2] }];
set_property -dict { PACKAGE_PIN B6     IOSTANDARD LVCMOS33 } [get_ports { cart_bank3[3] }];

# Cartridge individual signals
# Pin 30: nRST (GB) / nCS2 (GBA)
set_property -dict { PACKAGE_PIN E15    IOSTANDARD LVCMOS33 } [get_ports { cart_pin30 }];
set_property -dict { PACKAGE_PIN C16    IOSTANDARD LVCMOS33 } [get_ports { cart_pin30_dir }];

# Pin 31: VIN (GB) / nIRQ (GBA)
set_property -dict { PACKAGE_PIN F16    IOSTANDARD LVCMOS33 } [get_ports { cart_pin31 }];
set_property -dict { PACKAGE_PIN F15    IOSTANDARD LVCMOS33 } [get_ports { cart_pin31_dir }];

# Cartridge bank directions
set_property -dict { PACKAGE_PIN D15    IOSTANDARD LVCMOS33 } [get_ports { cart_bank0_dir }];
set_property -dict { PACKAGE_PIN A11    IOSTANDARD LVCMOS33 } [get_ports { cart_bank1_dir }];
set_property -dict { PACKAGE_PIN F6     IOSTANDARD LVCMOS33 } [get_ports { cart_bank2_dir }];
set_property -dict { PACKAGE_PIN B4     IOSTANDARD LVCMOS33 } [get_ports { cart_bank3_dir }];

# Cartridge configuration
set_property -dict { PACKAGE_PIN J13    IOSTANDARD LVCMOS33 } [get_ports { cart_switch }];
set_property -dict { PACKAGE_PIN A5     IOSTANDARD LVCMOS33 } [get_ports { cart_oe_n   }];


########################################
# Link Port
########################################
set_property -dict { PACKAGE_PIN K15     IOSTANDARD LVCMOS33 } [get_ports { link_so     }];
set_property -dict { PACKAGE_PIN J15     IOSTANDARD LVCMOS33 } [get_ports { link_si     }];
set_property -dict { PACKAGE_PIN H15     IOSTANDARD LVCMOS33 } [get_ports { link_sd     }];
set_property -dict { PACKAGE_PIN G16     IOSTANDARD LVCMOS33 } [get_ports { link_sc     }];
set_property -dict { PACKAGE_PIN K16     IOSTANDARD LVCMOS33 } [get_ports { link_so_dir }];
set_property -dict { PACKAGE_PIN J14     IOSTANDARD LVCMOS33 } [get_ports { link_si_dir }];
set_property -dict { PACKAGE_PIN H14     IOSTANDARD LVCMOS33 } [get_ports { link_sd_dir }];
set_property -dict { PACKAGE_PIN G14     IOSTANDARD LVCMOS33 } [get_ports { link_sc_dir }];

########################################
# LCD
########################################
set_property -dict { PACKAGE_PIN T18     IOSTANDARD LVCMOS33 } [get_ports { lcd_dotclk  }];
set_property -dict { PACKAGE_PIN U18     IOSTANDARD LVCMOS33 } [get_ports { lcd_hsync   }];
set_property -dict { PACKAGE_PIN T16     IOSTANDARD LVCMOS33 } [get_ports { lcd_vsync   }];
set_property -dict { PACKAGE_PIN R18     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_en }];
set_property -dict { PACKAGE_PIN R17     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_b[0] }];
set_property -dict { PACKAGE_PIN P18     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_b[1] }];
set_property -dict { PACKAGE_PIN N17     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_b[2] }];
set_property -dict { PACKAGE_PIN M17     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_b[3] }];
set_property -dict { PACKAGE_PIN M18     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_b[4] }];
set_property -dict { PACKAGE_PIN L16     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_b[5] }];
set_property -dict { PACKAGE_PIN L18     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_b[6] }];
set_property -dict { PACKAGE_PIN K17     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_b[7] }];
set_property -dict { PACKAGE_PIN J17     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_g[0] }];
set_property -dict { PACKAGE_PIN J18     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_g[1] }];
set_property -dict { PACKAGE_PIN H16     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_g[2] }];
set_property -dict { PACKAGE_PIN H17     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_g[3] }];
set_property -dict { PACKAGE_PIN G18     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_g[4] }];
set_property -dict { PACKAGE_PIN G17     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_g[5] }];
set_property -dict { PACKAGE_PIN F18     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_g[6] }];
set_property -dict { PACKAGE_PIN E17     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_g[7] }];
set_property -dict { PACKAGE_PIN E18     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_r[0] }];
set_property -dict { PACKAGE_PIN E16     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_r[1] }];
set_property -dict { PACKAGE_PIN D18     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_r[2] }];
set_property -dict { PACKAGE_PIN D17     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_r[3] }];
set_property -dict { PACKAGE_PIN C17     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_r[4] }];
set_property -dict { PACKAGE_PIN B18     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_r[5] }];
set_property -dict { PACKAGE_PIN B17     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_r[6] }];
set_property -dict { PACKAGE_PIN A18     IOSTANDARD LVCMOS33 } [get_ports { lcd_data_r[7] }];

########################################
# Buttons
########################################
set_property -dict { PACKAGE_PIN L6      IOSTANDARD LVCMOS33 } [get_ports { btn_a      }];
set_property -dict { PACKAGE_PIN K6      IOSTANDARD LVCMOS33 } [get_ports { btn_b      }];
set_property -dict { PACKAGE_PIN M6      IOSTANDARD LVCMOS33 } [get_ports { btn_x      }];
set_property -dict { PACKAGE_PIN N5      IOSTANDARD LVCMOS33 } [get_ports { btn_y      }];
set_property -dict { PACKAGE_PIN N16     IOSTANDARD LVCMOS33 } [get_ports { btn_up     }];
set_property -dict { PACKAGE_PIN L13     IOSTANDARD LVCMOS33 } [get_ports { btn_down   }];
set_property -dict { PACKAGE_PIN L14     IOSTANDARD LVCMOS33 } [get_ports { btn_left   }];
set_property -dict { PACKAGE_PIN M16     IOSTANDARD LVCMOS33 } [get_ports { btn_right  }];
set_property -dict { PACKAGE_PIN K13     IOSTANDARD LVCMOS33 } [get_ports { btn_l      }];
set_property -dict { PACKAGE_PIN K5      IOSTANDARD LVCMOS33 } [get_ports { btn_r      }];
set_property -dict { PACKAGE_PIN H6      IOSTANDARD LVCMOS33 } [get_ports { btn_start  }];
set_property -dict { PACKAGE_PIN H5      IOSTANDARD LVCMOS33 } [get_ports { btn_select }];
set_property PULLTYPE PULLUP [get_ports btn_*];

########################################
# DAC I2S
########################################
set_property -dict { PACKAGE_PIN T15     IOSTANDARD LVCMOS33 } [get_ports { dac_mclk }];
set_property -dict { PACKAGE_PIN R15     IOSTANDARD LVCMOS33 } [get_ports { dac_wclk }];
set_property -dict { PACKAGE_PIN R16     IOSTANDARD LVCMOS33 } [get_ports { dac_bclk }];
set_property -dict { PACKAGE_PIN P15     IOSTANDARD LVCMOS33 } [get_ports { dac_din  }];

########################################
# MCU Communication
########################################
set_property -dict { PACKAGE_PIN T14     IOSTANDARD LVCMOS33 } [get_ports { mcu_spi_clk  }];
set_property -dict { PACKAGE_PIN U17     IOSTANDARD LVCMOS33 } [get_ports { mcu_spi_cs_n }];
set_property -dict { PACKAGE_PIN V15     IOSTANDARD LVCMOS33 } [get_ports { mcu_spi_d[0] }];
set_property -dict { PACKAGE_PIN V16     IOSTANDARD LVCMOS33 } [get_ports { mcu_spi_d[1] }];
set_property -dict { PACKAGE_PIN U16     IOSTANDARD LVCMOS33 } [get_ports { mcu_spi_d[2] }];
set_property -dict { PACKAGE_PIN V17     IOSTANDARD LVCMOS33 } [get_ports { mcu_spi_d[3] }];
set_property -dict { PACKAGE_PIN N15     IOSTANDARD LVCMOS33 } [get_ports { mcu_irq_n    }];

########################################
# USB-C / HDMI
########################################
# Note: none of D0, D1, D2, CLK are swapped
# However, due to dock, they're all reversed.
# TODO parametrize it
set_property -dict { PACKAGE_PIN C2      IOSTANDARD TMDS_33  } [get_ports { hdmi_clk_p     }];
set_property -dict { PACKAGE_PIN C1      IOSTANDARD TMDS_33  } [get_ports { hdmi_clk_n     }];
set_property -dict { PACKAGE_PIN A4      IOSTANDARD TMDS_33  } [get_ports { hdmi_data_p[0] }];
set_property -dict { PACKAGE_PIN A3      IOSTANDARD TMDS_33  } [get_ports { hdmi_data_n[0] }];
set_property -dict { PACKAGE_PIN B3      IOSTANDARD TMDS_33  } [get_ports { hdmi_data_p[1] }];
set_property -dict { PACKAGE_PIN B2      IOSTANDARD TMDS_33  } [get_ports { hdmi_data_n[1] }];
set_property -dict { PACKAGE_PIN B1      IOSTANDARD TMDS_33  } [get_ports { hdmi_data_p[2] }];
set_property -dict { PACKAGE_PIN A1      IOSTANDARD TMDS_33  } [get_ports { hdmi_data_n[2] }];

set_property -dict { PACKAGE_PIN G13    IOSTANDARD LVCMOS33 } [get_ports { usb_sbu_1 }];
set_property -dict { PACKAGE_PIN F14    IOSTANDARD LVCMOS33 } [get_ports { usb_sbu_2 }];

########################################
# Vibration
########################################
set_property -dict { PACKAGE_PIN F5     IOSTANDARD LVCMOS33 } [get_ports { vibrate_in1 }];
set_property -dict { PACKAGE_PIN G6     IOSTANDARD LVCMOS33 } [get_ports { vibrate_in2 }];

########################################
# PMOD
########################################
set_property -dict { PACKAGE_PIN V14    IOSTANDARD LVCMOS33 } [get_ports { pmod[0] }];
set_property -dict { PACKAGE_PIN U14    IOSTANDARD LVCMOS33 } [get_ports { pmod[1] }];
set_property -dict { PACKAGE_PIN U13    IOSTANDARD LVCMOS33 } [get_ports { pmod[2] }];
set_property -dict { PACKAGE_PIN R13    IOSTANDARD LVCMOS33 } [get_ports { pmod[3] }];

set_property -dict { PACKAGE_PIN M14    IOSTANDARD LVCMOS33 } [get_ports { tp[0]   }];
set_property -dict { PACKAGE_PIN M13    IOSTANDARD LVCMOS33 } [get_ports { tp[1]   }];
set_property -dict { PACKAGE_PIN N14    IOSTANDARD LVCMOS33 } [get_ports { tp[2]   }];
set_property -dict { PACKAGE_PIN P14    IOSTANDARD LVCMOS33 } [get_ports { tp[3]   }];

########################################
# SRAM
########################################
set_property -dict { PACKAGE_PIN V1     IOSTANDARD LVCMOS33 } [get_ports { sram_a[0]  }];
set_property -dict { PACKAGE_PIN U2     IOSTANDARD LVCMOS33 } [get_ports { sram_a[1]  }];
set_property -dict { PACKAGE_PIN V2     IOSTANDARD LVCMOS33 } [get_ports { sram_a[2]  }];
set_property -dict { PACKAGE_PIN U3     IOSTANDARD LVCMOS33 } [get_ports { sram_a[3]  }];
set_property -dict { PACKAGE_PIN U4     IOSTANDARD LVCMOS33 } [get_ports { sram_a[4]  }];
set_property -dict { PACKAGE_PIN V10    IOSTANDARD LVCMOS33 } [get_ports { sram_a[5]  }];
set_property -dict { PACKAGE_PIN U11    IOSTANDARD LVCMOS33 } [get_ports { sram_a[6]  }];
set_property -dict { PACKAGE_PIN V11    IOSTANDARD LVCMOS33 } [get_ports { sram_a[7]  }];
set_property -dict { PACKAGE_PIN U12    IOSTANDARD LVCMOS33 } [get_ports { sram_a[8]  }];
set_property -dict { PACKAGE_PIN V12    IOSTANDARD LVCMOS33 } [get_ports { sram_a[9]  }];
set_property -dict { PACKAGE_PIN T1     IOSTANDARD LVCMOS33 } [get_ports { sram_a[10] }];
set_property -dict { PACKAGE_PIN U1     IOSTANDARD LVCMOS33 } [get_ports { sram_a[11] }];
set_property -dict { PACKAGE_PIN R3     IOSTANDARD LVCMOS33 } [get_ports { sram_a[12] }];
set_property -dict { PACKAGE_PIN P5     IOSTANDARD LVCMOS33 } [get_ports { sram_a[13] }];
set_property -dict { PACKAGE_PIN T3     IOSTANDARD LVCMOS33 } [get_ports { sram_a[14] }];
set_property -dict { PACKAGE_PIN R11    IOSTANDARD LVCMOS33 } [get_ports { sram_a[15] }];
set_property -dict { PACKAGE_PIN R12    IOSTANDARD LVCMOS33 } [get_ports { sram_a[16] }];
set_property -dict { PACKAGE_PIN T13    IOSTANDARD LVCMOS33 } [get_ports { sram_a[17] }];

set_property -dict { PACKAGE_PIN T5     IOSTANDARD LVCMOS33 } [get_ports { sram_io[0]  }];
set_property -dict { PACKAGE_PIN V5     IOSTANDARD LVCMOS33 } [get_ports { sram_io[1]  }];
set_property -dict { PACKAGE_PIN U6     IOSTANDARD LVCMOS33 } [get_ports { sram_io[2]  }];
set_property -dict { PACKAGE_PIN V6     IOSTANDARD LVCMOS33 } [get_ports { sram_io[3]  }];
set_property -dict { PACKAGE_PIN U7     IOSTANDARD LVCMOS33 } [get_ports { sram_io[4]  }];
set_property -dict { PACKAGE_PIN V7     IOSTANDARD LVCMOS33 } [get_ports { sram_io[5]  }];
set_property -dict { PACKAGE_PIN U8     IOSTANDARD LVCMOS33 } [get_ports { sram_io[6]  }];
set_property -dict { PACKAGE_PIN U9     IOSTANDARD LVCMOS33 } [get_ports { sram_io[7]  }];
set_property -dict { PACKAGE_PIN T4     IOSTANDARD LVCMOS33 } [get_ports { sram_io[8]  }];
set_property -dict { PACKAGE_PIN R5     IOSTANDARD LVCMOS33 } [get_ports { sram_io[9]  }];
set_property -dict { PACKAGE_PIN R6     IOSTANDARD LVCMOS33 } [get_ports { sram_io[10] }];
set_property -dict { PACKAGE_PIN T6     IOSTANDARD LVCMOS33 } [get_ports { sram_io[11] }];
set_property -dict { PACKAGE_PIN R7     IOSTANDARD LVCMOS33 } [get_ports { sram_io[12] }];
set_property -dict { PACKAGE_PIN R8     IOSTANDARD LVCMOS33 } [get_ports { sram_io[13] }];
set_property -dict { PACKAGE_PIN T8     IOSTANDARD LVCMOS33 } [get_ports { sram_io[14] }];
set_property -dict { PACKAGE_PIN T9     IOSTANDARD LVCMOS33 } [get_ports { sram_io[15] }];

set_property -dict { PACKAGE_PIN V4     IOSTANDARD LVCMOS33 } [get_ports { sram_ce_n }];
set_property -dict { PACKAGE_PIN V9     IOSTANDARD LVCMOS33 } [get_ports { sram_we_n }];
set_property -dict { PACKAGE_PIN T11    IOSTANDARD LVCMOS33 } [get_ports { sram_oe_n }];
set_property -dict { PACKAGE_PIN R10    IOSTANDARD LVCMOS33 } [get_ports { sram_ub_n }];
set_property -dict { PACKAGE_PIN T10    IOSTANDARD LVCMOS33 } [get_ports { sram_lb_n }];

########################################
# SDRAM
########################################
set_property -dict { PACKAGE_PIN R2     IOSTANDARD LVCMOS33 } [get_ports { sdram_dq[0]  }];
set_property -dict { PACKAGE_PIN R1     IOSTANDARD LVCMOS33 } [get_ports { sdram_dq[1]  }];
set_property -dict { PACKAGE_PIN P2     IOSTANDARD LVCMOS33 } [get_ports { sdram_dq[2]  }];
set_property -dict { PACKAGE_PIN N2     IOSTANDARD LVCMOS33 } [get_ports { sdram_dq[3]  }];
set_property -dict { PACKAGE_PIN N1     IOSTANDARD LVCMOS33 } [get_ports { sdram_dq[4]  }];
set_property -dict { PACKAGE_PIN M2     IOSTANDARD LVCMOS33 } [get_ports { sdram_dq[5]  }];
set_property -dict { PACKAGE_PIN M1     IOSTANDARD LVCMOS33 } [get_ports { sdram_dq[6]  }];
set_property -dict { PACKAGE_PIN L3     IOSTANDARD LVCMOS33 } [get_ports { sdram_dq[7]  }];
set_property -dict { PACKAGE_PIN L4     IOSTANDARD LVCMOS33 } [get_ports { sdram_dq[8]  }];
set_property -dict { PACKAGE_PIN L5     IOSTANDARD LVCMOS33 } [get_ports { sdram_dq[9]  }];
set_property -dict { PACKAGE_PIN M4     IOSTANDARD LVCMOS33 } [get_ports { sdram_dq[10] }];
set_property -dict { PACKAGE_PIN M3     IOSTANDARD LVCMOS33 } [get_ports { sdram_dq[11] }];
set_property -dict { PACKAGE_PIN N6     IOSTANDARD LVCMOS33 } [get_ports { sdram_dq[12] }];
set_property -dict { PACKAGE_PIN N4     IOSTANDARD LVCMOS33 } [get_ports { sdram_dq[13] }];
set_property -dict { PACKAGE_PIN P3     IOSTANDARD LVCMOS33 } [get_ports { sdram_dq[14] }];
set_property -dict { PACKAGE_PIN P4     IOSTANDARD LVCMOS33 } [get_ports { sdram_dq[15] }];

set_property -dict { PACKAGE_PIN G2     IOSTANDARD LVCMOS33 } [get_ports { sdram_a[0]  }];
set_property -dict { PACKAGE_PIN F1     IOSTANDARD LVCMOS33 } [get_ports { sdram_a[1]  }];
set_property -dict { PACKAGE_PIN E2     IOSTANDARD LVCMOS33 } [get_ports { sdram_a[2]  }];
set_property -dict { PACKAGE_PIN E1     IOSTANDARD LVCMOS33 } [get_ports { sdram_a[3]  }];
set_property -dict { PACKAGE_PIN E7     IOSTANDARD LVCMOS33 } [get_ports { sdram_a[4]  }];
set_property -dict { PACKAGE_PIN D3     IOSTANDARD LVCMOS33 } [get_ports { sdram_a[5]  }];
set_property -dict { PACKAGE_PIN D2     IOSTANDARD LVCMOS33 } [get_ports { sdram_a[6]  }];
set_property -dict { PACKAGE_PIN E6     IOSTANDARD LVCMOS33 } [get_ports { sdram_a[7]  }];
set_property -dict { PACKAGE_PIN E3     IOSTANDARD LVCMOS33 } [get_ports { sdram_a[8]  }];
set_property -dict { PACKAGE_PIN F3     IOSTANDARD LVCMOS33 } [get_ports { sdram_a[9]  }];
set_property -dict { PACKAGE_PIN G1     IOSTANDARD LVCMOS33 } [get_ports { sdram_a[10] }];
set_property -dict { PACKAGE_PIN F4     IOSTANDARD LVCMOS33 } [get_ports { sdram_a[11] }];
set_property -dict { PACKAGE_PIN G3     IOSTANDARD LVCMOS33 } [get_ports { sdram_a[12] }];

set_property -dict { PACKAGE_PIN H1     IOSTANDARD LVCMOS33 } [get_ports { sdram_bs[0] }];
set_property -dict { PACKAGE_PIN H2     IOSTANDARD LVCMOS33 } [get_ports { sdram_bs[1] }];

set_property -dict { PACKAGE_PIN J5     IOSTANDARD LVCMOS33 } [get_ports { sdram_clk      }];
set_property -dict { PACKAGE_PIN K2     IOSTANDARD LVCMOS33 } [get_ports { sdram_we_n     }];
set_property -dict { PACKAGE_PIN L1     IOSTANDARD LVCMOS33 } [get_ports { sdram_ldqm     }];
set_property -dict { PACKAGE_PIN K3     IOSTANDARD LVCMOS33 } [get_ports { sdram_udqm     }];
set_property -dict { PACKAGE_PIN K1     IOSTANDARD LVCMOS33 } [get_ports { sdram_cas_n    }];
set_property -dict { PACKAGE_PIN J2     IOSTANDARD LVCMOS33 } [get_ports { sdram_ras_n    }];
set_property -dict { PACKAGE_PIN J4     IOSTANDARD LVCMOS33 } [get_ports { sdram_cke[0]   }];
set_property -dict { PACKAGE_PIN H4     IOSTANDARD LVCMOS33 } [get_ports { sdram_cke[1]   }];
set_property -dict { PACKAGE_PIN J3     IOSTANDARD LVCMOS33 } [get_ports { sdram_cs_n[0]  }];
set_property -dict { PACKAGE_PIN G4     IOSTANDARD LVCMOS33 } [get_ports { sdram_cs_n[1]  }];
