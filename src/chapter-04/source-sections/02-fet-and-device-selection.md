<!-- 来源：PDF 第 118 页；原书第 104 页 -->

![图 4.4　N 沟道结型 FET 的转移特性与输出特性](../images/fig-04-04.png)

#### 饱和区的工作

饱和区的漏极电流近似为：

\\[
I_D=I_{DSS}\left(1-\frac{V_{GS}}{V_P}\right)^2
\tag{4.2}
\\]

其中，\\(I_{DSS}\\) 是 \\(V_{GS}=0\\) 时的漏极电流，\\(V_P\\) 是夹断（Pinch-off）电压，即 \\(I_D=0\\) 时的栅极—源极间电压。

#### 线性区的工作

线性区的漏极电流近似为：

\\[
\begin{aligned}
I_D
&=\frac{I_{DSS}}{V_P^2}
\left[2(V_{GS}-V_P)-V_{DS}\right]V_{DS}
\end{aligned}
\tag{4.3}
\\]

#### \\(\pi\\) 型模型

FET 在饱和区的小信号等效电路可用图 4.5 的 \\(\pi\\) 型模型表示。对式（4.2）关于 \\(V_{GS}\\) 微分：

\\[
\begin{aligned}
g_m
&=\frac{dI_D}{dV_{GS}}\\
&=2\left(\frac{I_{DSS}}{-V_P}\right)
\left(1-\frac{V_{GS}}{V_P}\right)
\end{aligned}
\tag{4.4}
\\]

结合式（4.2）可得：

\\[
\begin{aligned}
g_m
&=\left(\frac{2\sqrt{I_{DSS}}}{-V_P}\right)\sqrt{I_D}
\end{aligned}
\tag{4.5}
\\]

可见 FET 的 \\(g_m\\) 与漏极电流的平方根成正比。

<!-- 来源：PDF 第 119 页；原书第 105 页 -->

### 4.3.2　Cascode 电路的电压增益与频率特性

![图 4.5　饱和区 FET 的小信号 \\(\pi\\) 型等效电路](../images/fig-04-05.png)

FET 与双极性晶体管组成的 Cascode 电路，可由图 4.5 与第 3 章附录 B 的基极接地等效电路组合成图 4.6。

图 4.6(a) 中，\\(C_{GD}\\) 的米勒效应产生的等效输入电容为：

\\[
\begin{aligned}
C_{\mathrm{in}}
&=C_{GD}(1+A)\\
&=C_{GD}(1+g_mr_e)
\end{aligned}
\tag{4.6}
\\]

![图 4.6　FET 与双极性晶体管组成的 Cascode 小信号等效电路](../images/fig-04-06.png)

从表 4.2 中选用 \\(\mu\mathrm{PA63H}\\)，并令漏极电流为 \\(2\ \mathrm{mA}\\)。由图 4.7 可读得 \\(I_{DSS}=6\ \mathrm{mA}\\)、\\(V_P=-1.2\ \mathrm{V}\\)。

<!-- 来源：PDF 第 120 页；原书第 106 页 -->

代入式（4.5）：

\\[
\begin{aligned}
g_m
&=\left(\frac{2\sqrt{6\times10^{-3}}}{1.2}\right)
\sqrt{2\times10^{-3}}\\
&=5.77\ \mathrm{mS}
\end{aligned}
\tag{4.7}
\\]

![图 4.7　\\(\mu\mathrm{PA63H}\\) 的 \\(I_D-V_{GS}\\) 特性](../images/fig-04-07.png)

由第 3 章附录 B 式（B.2），基极接地输入电阻 \\(r_e\\) 为：

\\[
\begin{aligned}
r_e
&=\frac{26}{1000\times2\times10^{-3}}\\
&=13\ \Omega
\end{aligned}
\tag{4.8}
\\]

将 \\(g_m=5.77\ \mathrm{mS}\\)、\\(r_e=13\ \Omega\\) 代入式（4.6）：

\\[
\begin{aligned}
C_{\mathrm{in}}
&=C_{GD}(1+g_mr_e)\\
&=1.075C_{GD}\\
&\approx C_{GD}
\end{aligned}
\tag{4.9}
\\]

可见米勒效应小到可以忽略。因此图 4.6(a) 可简化为图 4.6(b)，再把从属电流源合并为图 4.6(c) 的等效电路。Folded Cascode 也可使用同一小信号等效电路分析。

### 4.3.3　初级 FET 的选择

转换速率由共源电流 \\(I_1\\) 与相位补偿电容 \\(C_f\\) 决定：

\\[
\mathrm{SR}=\frac{I_1}{C_f}
\tag{4.10}
\\]

为了满足 \\(\mathrm{SR}=400\ \mathrm{V/\mu s}\\)，规定

\\[
I_1=4\ \mathrm{mA},\qquad C_f=10\ \mathrm{pF}.
\\]

由于使用差动结构，每只 FET 的漏极电流自动成为 \\(2\ \mathrm{mA}\\)。

<!-- 来源：PDF 第 121 页；原书第 107 页 -->

当信号源电阻 \\(R_S=0\\)，且晶体管输出电容远小于相位补偿电容 \\(C_f\\) 时，高频开环增益的绝对值为：

\\[
|A|=g_m\left(\frac{1}{2\pi fC_f}\right)
\tag{4.11}
\\]

根据目标规格，在 \\(8\ \mathrm{MHz}\\) 处开环增益必须约为 10。代入 \\(A=10\\)、\\(f=8\times10^6\ \mathrm{Hz}\\)、\\(C_f=10\times10^{-12}\ \mathrm{F}\\)，得 \\(g_m=5.02\ \mathrm{mS}\\)，因此选择 \\(\mu\mathrm{PA63H}\\)。其他候选 FET 的 \\(g_m\\) 较大；若把 \\(g_m\\) 降到约 \\(5\ \mathrm{mS}\\)，必须降低 \\(I_D\\)，同时也会降低转换速率。

### 4.3.4　第二级晶体管 \\(Tr_1\\)、\\(Tr_2\\) 与输出级 \\(Tr_5\\)、\\(Tr_6\\)

图 4.2 第二级晶体管的集电极电流 \\(I_C\\) 宜为初级 FET 漏极电流的 2～3 倍，因此取 \\(5\ \mathrm{mA}\\)。恒流电路电流为：

\\[
I_2=I_3=I_D+I_C=2+5=7\ \mathrm{mA}.
\\]

取正电源 \\(V_{CC}=50\ \mathrm{V}\\)、第二级偏置 \\(V_{B1}=6\ \mathrm{V}\\)，则 \\(Tr_1\\)、\\(Tr_2\\) 的平均功耗为：

\\[
P_C=V_{CE}I_C=(50-6)\times5\ \mathrm{mA}=220\ \mathrm{mW}.
\\]

瞬时最大功耗可能达到约 \\(440\ \mathrm{mW}\\)，因此应使用 \\(P_C=800\ \mathrm{mW}\\) 级、\\(V_{CEO}\ge120\ \mathrm{V}\\) 的晶体管。第二级选用低 \\(C_{ob}\\)、高耐压的 2SA1145，电流镜采用其互补器件 2SC2705。输出级采用低 \\(C_{ob}\\) 的 2SA1209/2SC2911，并按 A 类工作要求选用 \\(P_C\ge5\ \mathrm{W}\\) 的器件。

<!-- 来源：PDF 第 122 页；原书第 108 页 -->

![表 4.3　所使用晶体管的绝对最大额定值](../images/table-04-03.png)

## 4.4　应对基本电路充实内容

图 4.2 只是基本架构。为了得到可实际工作的放大器，还需要加入输入级保护与自举、失真抵消、相位补偿和输出级设计等内容。

### 4.4.1　初级应做成 Cascode Bootstrap

N 沟道结型 FET 的栅极—沟道间是 PN 结，存在流向栅极的漏电流。漏极—源极间电压升高时，栅极漏电流会急剧增加。

![图 4.8　N 沟道结型 FET 的构造示意图](../images/fig-04-08.png)
