import { useState, useEffect, useCallback, useRef } from "react";

// ============================================================
// PDF GENERATOR (jsPDF)
// ============================================================
const loadJsPDF = () => {
  return new Promise((resolve) => {
    if (window.jspdf) return resolve(window.jspdf.jsPDF);
    const s = document.createElement("script");
    s.src = "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js";
    s.onload = () => resolve(window.jspdf.jsPDF);
    document.head.appendChild(s);
  });
};

const generatePDF = async (cotizacion, empresa) => {
  const jsPDF = await loadJsPDF();
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  const W = 210;
  const margin = 20;
  const contentW = W - margin * 2;
  let y = 20;
  const fmt = (n) => `${empresa.simbolo} ${Number(n).toLocaleString("es-AR", { minimumFractionDigits: 0 })}`;

  // --- HEADER BAND ---
  doc.setFillColor(15, 23, 42);
  doc.rect(0, 0, W, 42, "F");
  doc.setFillColor(37, 99, 235);
  doc.rect(0, 42, W, 1.5, "F");

  doc.setFont("helvetica", "bold");
  doc.setFontSize(22);
  doc.setTextColor(241, 245, 249);
  doc.text(empresa.nombre, margin, 18);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.setTextColor(148, 163, 184);
  doc.text("COTIZACIÓN", margin, 27);

  doc.setFont("helvetica", "bold");
  doc.setFontSize(14);
  doc.setTextColor(96, 165, 250);
  doc.text(cotizacion.cotizacion_id, margin, 36);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.setTextColor(148, 163, 184);
  doc.text(`Fecha: ${cotizacion.fecha}`, W - margin, 27, { align: "right" });
  doc.text(`Vendedor: ${cotizacion.usuario_nombre}`, W - margin, 36, { align: "right" });

  y = 54;

  // --- DATOS CLIENTE ---
  doc.setFillColor(241, 245, 249);
  doc.roundedRect(margin, y, contentW, 24, 2, 2, "F");
  doc.setFont("helvetica", "bold");
  doc.setFontSize(9);
  doc.setTextColor(100, 116, 139);
  doc.text("CLIENTE", margin + 6, y + 7);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.setTextColor(15, 23, 42);
  doc.text(cotizacion.cliente_nombre || "—", margin + 6, y + 16);
  if (cotizacion.cliente_contacto) {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.setTextColor(100, 116, 139);
    doc.text(cotizacion.cliente_contacto, margin + 6, y + 21);
  }

  // Implemento en la derecha
  doc.setFont("helvetica", "bold");
  doc.setFontSize(9);
  doc.setTextColor(100, 116, 139);
  doc.text("IMPLEMENTO", W - margin - 6, y + 7, { align: "right" });
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.setTextColor(15, 23, 42);
  doc.text(cotizacion.producto_nombre, W - margin - 6, y + 16, { align: "right" });
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.setTextColor(100, 116, 139);
  doc.text(cotizacion.categoria, W - margin - 6, y + 21, { align: "right" });

  y += 34;

  // --- TABLE HEADER ---
  doc.setFillColor(15, 23, 42);
  doc.roundedRect(margin, y, contentW, 9, 1.5, 1.5, "F");
  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  doc.setTextColor(241, 245, 249);
  doc.text("DESCRIPCIÓN", margin + 6, y + 6);
  doc.text("IMPORTE", W - margin - 6, y + 6, { align: "right" });
  y += 13;

  // --- PRECIO BASE ---
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.setTextColor(30, 41, 59);
  doc.text(`Precio base — ${cotizacion.producto_nombre}`, margin + 6, y);
  doc.setFont("helvetica", "bold");
  doc.text(fmt(cotizacion.precio_base), W - margin - 6, y, { align: "right" });
  y += 8;

  // --- OPCIONALES ---
  if (cotizacion.detalle && cotizacion.detalle.length > 0) {
    cotizacion.detalle.forEach((d, i) => {
      if (i % 2 === 0) {
        doc.setFillColor(248, 250, 252);
        doc.rect(margin, y - 4, contentW, 8, "F");
      }
      doc.setFont("helvetica", "normal");
      doc.setFontSize(10);
      doc.setTextColor(71, 85, 105);
      doc.text(`+ ${d.nombre}`, margin + 10, y);
      doc.setTextColor(30, 41, 59);
      doc.setFont("helvetica", "bold");
      doc.text(fmt(d.precio), W - margin - 6, y, { align: "right" });
      y += 8;
    });
  }

  // --- SEPARATOR ---
  y += 2;
  doc.setDrawColor(226, 232, 240);
  doc.setLineWidth(0.3);
  doc.line(margin, y, W - margin, y);
  y += 8;

  // --- SUBTOTAL ---
  const drawLine = (label, value, bold, color) => {
    doc.setFont("helvetica", bold ? "bold" : "normal");
    doc.setFontSize(bold ? 11 : 10);
    doc.setTextColor(...(color || [30, 41, 59]));
    doc.text(label, margin + 6, y);
    doc.text(value, W - margin - 6, y, { align: "right" });
    y += bold ? 9 : 7;
  };

  drawLine("Subtotal", fmt(cotizacion.subtotal), false);

  if (cotizacion.bonificacion_pct > 0) {
    drawLine(`Bonificación (${cotizacion.bonificacion_pct}%)`, `- ${fmt(cotizacion.bonificacion_monto)}`, false, [34, 197, 94]);
    drawLine("Subtotal bonificado", fmt(cotizacion.subtotal_bonificado), false);
  }

  drawLine(`IVA (${cotizacion.iva_pct}%)`, fmt(cotizacion.iva_monto), false, [100, 116, 139]);

  // --- TOTAL FINAL ---
  y += 2;
  doc.setFillColor(37, 99, 235);
  doc.roundedRect(margin, y, contentW, 14, 2, 2, "F");
  doc.setFont("helvetica", "bold");
  doc.setFontSize(13);
  doc.setTextColor(255, 255, 255);
  doc.text("TOTAL FINAL", margin + 8, y + 9.5);
  doc.setFontSize(15);
  doc.text(fmt(cotizacion.total_final), W - margin - 8, y + 9.5, { align: "right" });

  y += 24;

  // --- OBSERVACIONES ---
  if (empresa.observaciones_default) {
    doc.setFillColor(248, 250, 252);
    const obsLines = doc.splitTextToSize(empresa.observaciones_default, contentW - 16);
    const obsH = obsLines.length * 5 + 14;
    doc.roundedRect(margin, y, contentW, obsH, 2, 2, "F");
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8);
    doc.setTextColor(100, 116, 139);
    doc.text("CONDICIONES COMERCIALES", margin + 8, y + 7);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.setTextColor(71, 85, 105);
    doc.text(obsLines, margin + 8, y + 14);
    y += obsH + 4;
  }

  if (cotizacion.notas) {
    doc.setFont("helvetica", "italic");
    doc.setFontSize(9);
    doc.setTextColor(100, 116, 139);
    const notaLines = doc.splitTextToSize(`Nota: ${cotizacion.notas}`, contentW - 12);
    doc.text(notaLines, margin + 6, y + 4);
  }

  // --- FOOTER ---
  doc.setFillColor(248, 250, 252);
  doc.rect(0, 282, W, 15, "F");
  doc.setFont("helvetica", "normal");
  doc.setFontSize(7);
  doc.setTextColor(148, 163, 184);
  doc.text(`${empresa.nombre} · Documento generado automáticamente · ${cotizacion.cotizacion_id}`, W / 2, 289, { align: "center" });

  // --- RETURN BASE64 for preview ---
  const pdfBase64 = doc.output("datauristring");
  return pdfBase64;
};

// ============================================================
// PDF PREVIEW MODAL
// ============================================================
const PDFPreview = ({ dataUri, onClose, cotId }) => {
  if (!dataUri) return null;
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.8)", backdropFilter: "blur(8px)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
      <div style={{ width: "100%", maxWidth: 800, height: "90vh", background: "#1e293b", borderRadius: 16, border: "1px solid rgba(255,255,255,0.1)", overflow: "hidden", display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 20px", background: "rgba(0,0,0,0.3)", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <span style={{ color: "#f1f5f9", fontSize: 14, fontWeight: 600 }}>📄 {cotId || "Cotización"}</span>
          <div style={{ display: "flex", gap: 8 }}>
            <a href={dataUri} download={`${cotId || "cotizacion"}.pdf`}
              style={{ padding: "8px 16px", background: "rgba(34,197,94,0.15)", color: "#22c55e", border: "1px solid rgba(34,197,94,0.3)", borderRadius: 8, fontSize: 12, cursor: "pointer", textDecoration: "none", fontWeight: 500 }}>
              ⬇ Descargar
            </a>
            <button onClick={onClose}
              style={{ padding: "8px 16px", background: "rgba(239,68,68,0.1)", color: "#f87171", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 8, fontSize: 12, cursor: "pointer" }}>
              ✕ Cerrar
            </button>
          </div>
        </div>
        <iframe src={dataUri} style={{ flex: 1, border: "none", background: "#fff" }} title="PDF Preview" />
      </div>
    </div>
  );
};

// ============================================================
// DATA SIMULADA (en producción viene de Google Sheets)
// ============================================================
const DB = {
  empresas: [
    { empresa_id: "EMP-001", nombre: "TolvaMax S.A.", moneda: "ARS", simbolo: "$", iva_porcentaje: 21, bonif_max_porcentaje: 10, observaciones_default: "Precios sujetos a modificación sin previo aviso.\nValidez de la cotización: 15 días.\nForma de pago: 50% anticipo, 50% contra entrega." },
  ],
  usuarios: [
    { usuario_id: "USR-001", empresa_id: "EMP-001", nombre: "Carlos Pérez", email: "admin@tolvamax.com", password: "admin123", rol: "admin" },
    { usuario_id: "USR-002", empresa_id: "EMP-001", nombre: "María López", email: "vendedor@tolvamax.com", password: "venta123", rol: "vendedor" },
    { usuario_id: "USR-003", empresa_id: "EMP-001", nombre: "Juan Rodríguez", email: "dueno@tolvamax.com", password: "dueno123", rol: "dueno" },
  ],
  categorias: [
    { categoria_id: "CAT-001", empresa_id: "EMP-001", nombre: "Tolvas", icono: "🚛", orden: 1 },
    { categoria_id: "CAT-002", empresa_id: "EMP-001", nombre: "Semilleros", icono: "🌾", orden: 2 },
  ],
  productos: [
    { producto_id: "PROD-001", empresa_id: "EMP-001", categoria_id: "CAT-001", nombre: "Tolva 18 TN", precio_base: 15000000 },
    { producto_id: "PROD-002", empresa_id: "EMP-001", categoria_id: "CAT-001", nombre: "Tolva 20 TN", precio_base: 17500000 },
    { producto_id: "PROD-003", empresa_id: "EMP-001", categoria_id: "CAT-001", nombre: "Tolva 23 TN", precio_base: 20000000 },
    { producto_id: "PROD-004", empresa_id: "EMP-001", categoria_id: "CAT-001", nombre: "Tolva 26 TN", precio_base: 23000000 },
    { producto_id: "PROD-005", empresa_id: "EMP-001", categoria_id: "CAT-001", nombre: "Tolva 28 TN", precio_base: 25500000 },
    { producto_id: "PROD-006", empresa_id: "EMP-001", categoria_id: "CAT-001", nombre: "Tolva 33 TN", precio_base: 30000000 },
    { producto_id: "PROD-007", empresa_id: "EMP-001", categoria_id: "CAT-002", nombre: "Semillero SM-100", precio_base: 8000000 },
    { producto_id: "PROD-008", empresa_id: "EMP-001", categoria_id: "CAT-002", nombre: "Semillero SM-200", precio_base: 11500000 },
  ],
  grupos: [
    { grupo_id: "GRP-001", empresa_id: "EMP-001", nombre: "Eje delantero", tipo_seleccion: "unico", orden: 1, categoria_id: "CAT-001" },
    { grupo_id: "GRP-002", empresa_id: "EMP-001", nombre: "Sinfines cementados", tipo_seleccion: "unico", orden: 2, categoria_id: "CAT-001" },
    { grupo_id: "GRP-003", empresa_id: "EMP-001", nombre: "Rodado", tipo_seleccion: "multiple", max_seleccion: 2, orden: 3, categoria_id: "CAT-001" },
    { grupo_id: "GRP-004", empresa_id: "EMP-001", nombre: "Balanza", tipo_seleccion: "unico", orden: 4, categoria_id: "CAT-001" },
    { grupo_id: "GRP-005", empresa_id: "EMP-001", nombre: "Accesorios", tipo_seleccion: "multiple", orden: 5, categoria_id: "CAT-001" },
    { grupo_id: "GRP-006", empresa_id: "EMP-001", nombre: "Configuración", tipo_seleccion: "multiple", orden: 1, categoria_id: "CAT-002" },
  ],
  opcionales: [
    { opcional_id: "OPC-001", empresa_id: "EMP-001", grupo_id: "GRP-001", nombre: "Con eje delantero", precio: 1200000, incluido: false },
    { opcional_id: "OPC-002", empresa_id: "EMP-001", grupo_id: "GRP-001", nombre: "Sin eje delantero", precio: 0, incluido: true },
    { opcional_id: "OPC-003", empresa_id: "EMP-001", grupo_id: "GRP-002", nombre: "Con sinfines cementados", precio: 800000, incluido: false },
    { opcional_id: "OPC-004", empresa_id: "EMP-001", grupo_id: "GRP-002", nombre: "Sin sinfines cementados", precio: 0, incluido: true },
    { opcional_id: "OPC-005", empresa_id: "EMP-001", grupo_id: "GRP-003", nombre: "Rodado 22.5\"", precio: 950000, incluido: false },
    { opcional_id: "OPC-006", empresa_id: "EMP-001", grupo_id: "GRP-003", nombre: "Rodado 24.5\"", precio: 1100000, incluido: false },
    { opcional_id: "OPC-007", empresa_id: "EMP-001", grupo_id: "GRP-003", nombre: "Rodado 19.5\"", precio: 750000, incluido: false },
    { opcional_id: "OPC-008", empresa_id: "EMP-001", grupo_id: "GRP-004", nombre: "Balanza Magris", precio: 2500000, incluido: false },
    { opcional_id: "OPC-009", empresa_id: "EMP-001", grupo_id: "GRP-004", nombre: "Balanza Acromet", precio: 2800000, incluido: false },
    { opcional_id: "OPC-010", empresa_id: "EMP-001", grupo_id: "GRP-004", nombre: "Sin balanza", precio: 0, incluido: true },
    { opcional_id: "OPC-011", empresa_id: "EMP-001", grupo_id: "GRP-005", nombre: "Cajón porta herramientas", precio: 350000, incluido: false },
    { opcional_id: "OPC-012", empresa_id: "EMP-001", grupo_id: "GRP-005", nombre: "Depósito de agua 200L", precio: 420000, incluido: false },
    { opcional_id: "OPC-013", empresa_id: "EMP-001", grupo_id: "GRP-005", nombre: "Avant tren direccional", precio: 1500000, incluido: false },
    { opcional_id: "OPC-014", empresa_id: "EMP-001", grupo_id: "GRP-005", nombre: "Escalera abatible", precio: 280000, incluido: false },
    { opcional_id: "OPC-015", empresa_id: "EMP-001", grupo_id: "GRP-006", nombre: "Lona cobertura", precio: 450000, incluido: false },
    { opcional_id: "OPC-016", empresa_id: "EMP-001", grupo_id: "GRP-006", nombre: "Escalera acceso", precio: 320000, incluido: false },
  ],
  cotizaciones: [],
};

const fmt = (n, sym = "$") => `${sym} ${Number(n).toLocaleString("es-AR", { minimumFractionDigits: 0 })}`;

// ============================================================
// LOGIN SCREEN
// ============================================================
const LoginScreen = ({ onLogin }) => {
  const [email, setEmail] = useState("");
  const [pass, setPass] = useState("");
  const [error, setError] = useState("");

  const handleLogin = () => {
    const user = DB.usuarios.find(u => u.email === email && u.password === pass);
    if (user) { onLogin(user); }
    else { setError("Email o contraseña incorrectos"); }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%)", fontFamily: "'DM Sans', system-ui, sans-serif" }}>
      <div style={{ width: 400, background: "rgba(255,255,255,0.03)", backdropFilter: "blur(20px)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 20, padding: "48px 40px", boxShadow: "0 25px 60px rgba(0,0,0,0.4)" }}>
        <div style={{ textAlign: "center", marginBottom: 36 }}>
          <div style={{ fontSize: 36, marginBottom: 8 }}>🚛</div>
          <h1 style={{ color: "#f1f5f9", fontSize: 24, fontWeight: 700, margin: 0, letterSpacing: "-0.5px" }}>Cotizador</h1>
          <p style={{ color: "#64748b", fontSize: 14, margin: "8px 0 0" }}>Ingresá tus credenciales para continuar</p>
        </div>

        <div style={{ marginBottom: 20 }}>
          <label style={{ color: "#94a3b8", fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "1px", display: "block", marginBottom: 8 }}>Email</label>
          <input value={email} onChange={e => { setEmail(e.target.value); setError(""); }} placeholder="tu@email.com"
            style={{ width: "100%", padding: "14px 16px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, color: "#f1f5f9", fontSize: 15, outline: "none", boxSizing: "border-box", transition: "border 0.2s" }}
            onFocus={e => e.target.style.borderColor = "rgba(59,130,246,0.5)"}
            onBlur={e => e.target.style.borderColor = "rgba(255,255,255,0.1)"}
          />
        </div>

        <div style={{ marginBottom: 28 }}>
          <label style={{ color: "#94a3b8", fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "1px", display: "block", marginBottom: 8 }}>Contraseña</label>
          <input type="password" value={pass} onChange={e => { setPass(e.target.value); setError(""); }} placeholder="••••••••"
            onKeyDown={e => e.key === "Enter" && handleLogin()}
            style={{ width: "100%", padding: "14px 16px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, color: "#f1f5f9", fontSize: 15, outline: "none", boxSizing: "border-box", transition: "border 0.2s" }}
            onFocus={e => e.target.style.borderColor = "rgba(59,130,246,0.5)"}
            onBlur={e => e.target.style.borderColor = "rgba(255,255,255,0.1)"}
          />
        </div>

        {error && <div style={{ color: "#f87171", fontSize: 13, textAlign: "center", marginBottom: 16, padding: "10px", background: "rgba(248,113,113,0.1)", borderRadius: 8 }}>{error}</div>}

        <button onClick={handleLogin}
          style={{ width: "100%", padding: "14px", background: "linear-gradient(135deg, #3b82f6, #2563eb)", color: "#fff", border: "none", borderRadius: 12, fontSize: 15, fontWeight: 600, cursor: "pointer", transition: "all 0.2s", letterSpacing: "0.3px" }}
          onMouseOver={e => e.target.style.transform = "translateY(-1px)"}
          onMouseOut={e => e.target.style.transform = "translateY(0)"}
        >Iniciar sesión</button>

        <div style={{ marginTop: 24, padding: "16px", background: "rgba(59,130,246,0.08)", borderRadius: 10, border: "1px solid rgba(59,130,246,0.15)" }}>
          <p style={{ color: "#94a3b8", fontSize: 11, margin: 0, textAlign: "center", lineHeight: 1.6 }}>
            <strong style={{ color: "#60a5fa" }}>Demo:</strong><br />
            Vendedor: vendedor@tolvamax.com / venta123<br />
            Dueño: dueno@tolvamax.com / dueno123<br />
            Admin: admin@tolvamax.com / admin123
          </p>
        </div>
      </div>
    </div>
  );
};

// ============================================================
// TOPBAR
// ============================================================
const TopBar = ({ user, empresa, currentView, onNavigate, onLogout }) => {
  const canAdmin = user.rol === "admin" || user.rol === "dueno";
  const navItems = [
    { id: "cotizar", label: "Nueva cotización", icon: "➕" },
    { id: "historial", label: "Historial", icon: "📋" },
    ...(canAdmin ? [{ id: "admin", label: "Administrar precios", icon: "⚙️" }] : []),
  ];
  return (
    <div style={{ background: "rgba(15,23,42,0.95)", backdropFilter: "blur(12px)", borderBottom: "1px solid rgba(255,255,255,0.06)", padding: "0 28px", display: "flex", alignItems: "center", justifyContent: "space-between", height: 60, position: "sticky", top: 0, zIndex: 100 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
        <span style={{ fontSize: 20 }}>🚛</span>
        <span style={{ color: "#f1f5f9", fontWeight: 700, fontSize: 16, letterSpacing: "-0.3px" }}>{empresa.nombre}</span>
        <div style={{ display: "flex", gap: 4 }}>
          {navItems.map(n => (
            <button key={n.id} onClick={() => onNavigate(n.id)}
              style={{ padding: "8px 16px", background: currentView === n.id ? "rgba(59,130,246,0.2)" : "transparent", color: currentView === n.id ? "#60a5fa" : "#94a3b8", border: currentView === n.id ? "1px solid rgba(59,130,246,0.3)" : "1px solid transparent", borderRadius: 8, fontSize: 13, cursor: "pointer", fontWeight: currentView === n.id ? 600 : 400, transition: "all 0.2s", display: "flex", alignItems: "center", gap: 6 }}>
              <span>{n.icon}</span>{n.label}
            </button>
          ))}
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ textAlign: "right" }}>
          <div style={{ color: "#e2e8f0", fontSize: 13, fontWeight: 500 }}>{user.nombre}</div>
          <div style={{ color: "#64748b", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.5px" }}>{user.rol}</div>
        </div>
        <button onClick={onLogout} style={{ padding: "8px 14px", background: "rgba(239,68,68,0.1)", color: "#f87171", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 8, fontSize: 12, cursor: "pointer" }}>Salir</button>
      </div>
    </div>
  );
};

// ============================================================
// WIZARD - COTIZADOR
// ============================================================
const CotizadorWizard = ({ empresa, user, onSave }) => {
  const [step, setStep] = useState(0);
  const [categoria, setCategoria] = useState(null);
  const [producto, setProducto] = useState(null);
  const [selecciones, setSelecciones] = useState({});
  const [bonificacion, setBonificacion] = useState(0);
  const [clienteNombre, setClienteNombre] = useState("");
  const [clienteContacto, setClienteContacto] = useState("");
  const [notas, setNotas] = useState("");
  const [saved, setSaved] = useState(false);
  const [pdfUri, setPdfUri] = useState(null);

  const categorias = DB.categorias.filter(c => c.empresa_id === empresa.empresa_id);
  const productos = producto ? [] : DB.productos.filter(p => p.empresa_id === empresa.empresa_id && p.categoria_id === categoria?.categoria_id);
  const gruposDisponibles = producto ? DB.grupos.filter(g => g.empresa_id === empresa.empresa_id && g.categoria_id === categoria?.categoria_id) : [];
  const opcionalesPorGrupo = (gid) => DB.opcionales.filter(o => o.empresa_id === empresa.empresa_id && o.grupo_id === gid);

  useEffect(() => {
    if (producto && Object.keys(selecciones).length === 0) {
      const defaults = {};
      gruposDisponibles.forEach(g => {
        const opts = opcionalesPorGrupo(g.grupo_id);
        const def = opts.find(o => o.incluido);
        if (g.tipo_seleccion === "unico" && def) { defaults[g.grupo_id] = def.opcional_id; }
        else if (g.tipo_seleccion === "multiple") { defaults[g.grupo_id] = []; }
      });
      setSelecciones(defaults);
    }
  }, [producto]);

  const calcTotalOpcionales = () => {
    let total = 0;
    Object.entries(selecciones).forEach(([gid, val]) => {
      const grupo = DB.grupos.find(g => g.grupo_id === gid);
      if (!grupo) return;
      if (grupo.tipo_seleccion === "unico") {
        const opc = DB.opcionales.find(o => o.opcional_id === val);
        if (opc) total += opc.precio;
      } else if (Array.isArray(val)) {
        val.forEach(oid => { const opc = DB.opcionales.find(o => o.opcional_id === oid); if (opc) total += opc.precio; });
      }
    });
    return total;
  };

  const precioBase = producto?.precio_base || 0;
  const totalOpc = calcTotalOpcionales();
  const subtotal = precioBase + totalOpc;
  const bonifMonto = subtotal * (bonificacion / 100);
  const subtotalBonif = subtotal - bonifMonto;
  const ivaMonto = subtotalBonif * (empresa.iva_porcentaje / 100);
  const totalFinal = subtotalBonif + ivaMonto;

  const handleUnico = (gid, oid) => setSelecciones(prev => ({ ...prev, [gid]: oid }));
  const handleMultiple = (gid, oid, maxSel) => {
    setSelecciones(prev => {
      const current = prev[gid] || [];
      if (current.includes(oid)) return { ...prev, [gid]: current.filter(x => x !== oid) };
      if (maxSel && current.length >= maxSel) return prev;
      return { ...prev, [gid]: [...current, oid] };
    });
  };

  const handleSave = () => {
    const cotId = `COT-${String(DB.cotizaciones.length + 1).padStart(4, "0")}`;
    const detalle = [];
    Object.entries(selecciones).forEach(([gid, val]) => {
      const grupo = DB.grupos.find(g => g.grupo_id === gid);
      if (grupo?.tipo_seleccion === "unico") {
        const opc = DB.opcionales.find(o => o.opcional_id === val);
        if (opc && opc.precio > 0) detalle.push({ ...opc, cantidad: 1 });
      } else if (Array.isArray(val)) {
        val.forEach(oid => { const opc = DB.opcionales.find(o => o.opcional_id === oid); if (opc) detalle.push({ ...opc, cantidad: 1 }); });
      }
    });
    const cotizacion = {
      cotizacion_id: cotId, empresa_id: empresa.empresa_id, usuario_id: user.usuario_id, usuario_nombre: user.nombre,
      fecha: new Date().toISOString().split("T")[0], cliente_nombre: clienteNombre, cliente_contacto: clienteContacto,
      categoria: categoria.nombre, producto_nombre: producto.nombre, producto_id: producto.producto_id,
      precio_base: precioBase, total_opcionales: totalOpc, subtotal, bonificacion_pct: bonificacion,
      bonificacion_monto: bonifMonto, subtotal_bonificado: subtotalBonif, iva_pct: empresa.iva_porcentaje,
      iva_monto: ivaMonto, total_final: totalFinal, detalle, notas, estado: "emitida"
    };
    DB.cotizaciones.unshift(cotizacion);
    setSaved(true);
    if (onSave) onSave(cotizacion);
  };

  const reset = () => { setStep(0); setCategoria(null); setProducto(null); setSelecciones({}); setBonificacion(0); setClienteNombre(""); setClienteContacto(""); setNotas(""); setSaved(false); };

  const cardStyle = (selected) => ({
    padding: "20px 24px", background: selected ? "rgba(59,130,246,0.12)" : "rgba(255,255,255,0.03)",
    border: `1.5px solid ${selected ? "rgba(59,130,246,0.5)" : "rgba(255,255,255,0.06)"}`,
    borderRadius: 14, cursor: "pointer", transition: "all 0.25s ease",
    transform: selected ? "scale(1.01)" : "scale(1)",
  });

  const stepTitles = ["Categoría", "Modelo", "Configurar", "Datos cliente", "Resumen"];

  // SUCCESS
  if (saved) {
    const lastCot = DB.cotizaciones[0];
    return (
      <div style={{ maxWidth: 600, margin: "60px auto", textAlign: "center", padding: "0 20px" }}>
        {pdfUri && <PDFPreview dataUri={pdfUri} cotId={lastCot?.cotizacion_id} onClose={() => setPdfUri(null)} />}
        <div style={{ fontSize: 64, marginBottom: 20 }}>✅</div>
        <h2 style={{ color: "#f1f5f9", fontSize: 26, fontWeight: 700 }}>Cotización generada</h2>
        <p style={{ color: "#94a3b8", fontSize: 15, marginBottom: 32 }}>La cotización {lastCot?.cotizacion_id} fue registrada correctamente.</p>
        <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
          <button onClick={async () => { const uri = await generatePDF(lastCot, empresa); setPdfUri(uri); }}
            style={{ padding: "12px 28px", background: "linear-gradient(135deg, #22c55e, #16a34a)", color: "#fff", border: "none", borderRadius: 10, fontSize: 14, fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}>
            📄 Ver PDF
          </button>
          <button onClick={reset} style={{ padding: "12px 28px", background: "linear-gradient(135deg, #3b82f6, #2563eb)", color: "#fff", border: "none", borderRadius: 10, fontSize: 14, fontWeight: 600, cursor: "pointer" }}>Nueva cotización</button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "32px 20px" }}>
      {/* STEPPER */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, marginBottom: 40 }}>
        {stepTitles.map((t, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{
              width: 32, height: 32, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
              background: i === step ? "linear-gradient(135deg, #3b82f6, #2563eb)" : i < step ? "rgba(34,197,94,0.2)" : "rgba(255,255,255,0.05)",
              color: i <= step ? "#fff" : "#64748b", fontSize: 13, fontWeight: 600,
              border: i === step ? "none" : i < step ? "1px solid rgba(34,197,94,0.3)" : "1px solid rgba(255,255,255,0.1)"
            }}>{i < step ? "✓" : i + 1}</div>
            <span style={{ color: i === step ? "#f1f5f9" : "#64748b", fontSize: 13, fontWeight: i === step ? 600 : 400 }}>{t}</span>
            {i < stepTitles.length - 1 && <div style={{ width: 32, height: 1, background: "rgba(255,255,255,0.1)" }} />}
          </div>
        ))}
      </div>

      {/* STEP 0: CATEGORÍA */}
      {step === 0 && (
        <div>
          <h2 style={{ color: "#f1f5f9", fontSize: 22, fontWeight: 700, marginBottom: 8 }}>¿Qué querés cotizar?</h2>
          <p style={{ color: "#64748b", fontSize: 14, marginBottom: 28 }}>Seleccioná la categoría de implemento</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 16 }}>
            {categorias.map(c => (
              <div key={c.categoria_id} onClick={() => { setCategoria(c); setProducto(null); setSelecciones({}); setStep(1); }}
                style={{ ...cardStyle(false), textAlign: "center", padding: "32px 24px" }}
                onMouseOver={e => { e.currentTarget.style.borderColor = "rgba(59,130,246,0.4)"; e.currentTarget.style.transform = "translateY(-2px)"; }}
                onMouseOut={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)"; e.currentTarget.style.transform = "translateY(0)"; }}>
                <div style={{ fontSize: 40, marginBottom: 12 }}>{c.icono}</div>
                <div style={{ color: "#f1f5f9", fontSize: 18, fontWeight: 600 }}>{c.nombre}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* STEP 1: PRODUCTO */}
      {step === 1 && categoria && (
        <div>
          <h2 style={{ color: "#f1f5f9", fontSize: 22, fontWeight: 700, marginBottom: 8 }}>{categoria.icono} {categoria.nombre}</h2>
          <p style={{ color: "#64748b", fontSize: 14, marginBottom: 28 }}>Seleccioná el modelo</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 14 }}>
            {DB.productos.filter(p => p.categoria_id === categoria.categoria_id).map(p => (
              <div key={p.producto_id} onClick={() => { setProducto(p); setSelecciones({}); setStep(2); }}
                style={{ ...cardStyle(false), display: "flex", justifyContent: "space-between", alignItems: "center" }}
                onMouseOver={e => { e.currentTarget.style.borderColor = "rgba(59,130,246,0.4)"; e.currentTarget.style.transform = "translateY(-1px)"; }}
                onMouseOut={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)"; e.currentTarget.style.transform = "translateY(0)"; }}>
                <span style={{ color: "#f1f5f9", fontSize: 16, fontWeight: 600 }}>{p.nombre}</span>
                <span style={{ color: "#60a5fa", fontSize: 14, fontWeight: 500 }}>{fmt(p.precio_base, empresa.simbolo)}</span>
              </div>
            ))}
          </div>
          <button onClick={() => { setStep(0); setCategoria(null); }} style={{ marginTop: 24, padding: "10px 20px", background: "transparent", color: "#94a3b8", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 13, cursor: "pointer" }}>← Volver</button>
        </div>
      )}

      {/* STEP 2: OPCIONALES */}
      {step === 2 && producto && (
        <div>
          <h2 style={{ color: "#f1f5f9", fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Configurá tu {producto.nombre}</h2>
          <p style={{ color: "#64748b", fontSize: 14, marginBottom: 28 }}>Precio base: <strong style={{ color: "#60a5fa" }}>{fmt(precioBase, empresa.simbolo)}</strong></p>
          
          <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 28 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
              {gruposDisponibles.map(g => {
                const opts = opcionalesPorGrupo(g.grupo_id);
                return (
                  <div key={g.grupo_id} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 14, padding: "20px 24px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                      <h3 style={{ color: "#e2e8f0", fontSize: 15, fontWeight: 600, margin: 0 }}>{g.nombre}</h3>
                      {g.tipo_seleccion === "multiple" && g.max_seleccion && (
                        <span style={{ color: "#64748b", fontSize: 11, background: "rgba(255,255,255,0.05)", padding: "4px 10px", borderRadius: 6 }}>Máx. {g.max_seleccion}</span>
                      )}
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      {opts.map(o => {
                        const isSelected = g.tipo_seleccion === "unico"
                          ? selecciones[g.grupo_id] === o.opcional_id
                          : (selecciones[g.grupo_id] || []).includes(o.opcional_id);
                        return (
                          <div key={o.opcional_id}
                            onClick={() => g.tipo_seleccion === "unico" ? handleUnico(g.grupo_id, o.opcional_id) : handleMultiple(g.grupo_id, o.opcional_id, g.max_seleccion)}
                            style={{
                              padding: "12px 16px", borderRadius: 10, cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center",
                              background: isSelected ? "rgba(59,130,246,0.1)" : "rgba(255,255,255,0.02)",
                              border: `1px solid ${isSelected ? "rgba(59,130,246,0.35)" : "rgba(255,255,255,0.04)"}`, transition: "all 0.2s"
                            }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                              <div style={{
                                width: 20, height: 20, borderRadius: g.tipo_seleccion === "unico" ? "50%" : 5,
                                border: `2px solid ${isSelected ? "#3b82f6" : "rgba(255,255,255,0.2)"}`,
                                background: isSelected ? "#3b82f6" : "transparent", display: "flex", alignItems: "center", justifyContent: "center",
                                transition: "all 0.2s"
                              }}>{isSelected && <span style={{ color: "#fff", fontSize: 11 }}>✓</span>}</div>
                              <span style={{ color: isSelected ? "#f1f5f9" : "#cbd5e1", fontSize: 14 }}>{o.nombre}</span>
                            </div>
                            {o.precio > 0 && <span style={{ color: isSelected ? "#60a5fa" : "#64748b", fontSize: 13, fontWeight: 500 }}>+{fmt(o.precio, empresa.simbolo)}</span>}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* RESUMEN LATERAL */}
            <div style={{ position: "sticky", top: 80, alignSelf: "start" }}>
              <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 16, padding: "24px", backdropFilter: "blur(8px)" }}>
                <h3 style={{ color: "#f1f5f9", fontSize: 15, fontWeight: 600, margin: "0 0 16px" }}>Resumen</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "#94a3b8", fontSize: 13 }}>{producto.nombre}</span>
                    <span style={{ color: "#e2e8f0", fontSize: 13, fontWeight: 500 }}>{fmt(precioBase, empresa.simbolo)}</span>
                  </div>
                  {totalOpc > 0 && <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "#94a3b8", fontSize: 13 }}>Opcionales</span>
                    <span style={{ color: "#e2e8f0", fontSize: 13, fontWeight: 500 }}>+{fmt(totalOpc, empresa.simbolo)}</span>
                  </div>}
                  <div style={{ height: 1, background: "rgba(255,255,255,0.08)", margin: "4px 0" }} />
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "#f1f5f9", fontSize: 15, fontWeight: 700 }}>Total</span>
                    <span style={{ color: "#60a5fa", fontSize: 17, fontWeight: 700 }}>{fmt(subtotal, empresa.simbolo)}</span>
                  </div>
                  <div style={{ color: "#64748b", fontSize: 11, textAlign: "right" }}>+ IVA {empresa.iva_porcentaje}%</div>
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: "flex", gap: 12, marginTop: 28 }}>
            <button onClick={() => { setStep(1); setProducto(null); setSelecciones({}); }} style={{ padding: "10px 20px", background: "transparent", color: "#94a3b8", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 13, cursor: "pointer" }}>← Volver</button>
            <button onClick={() => setStep(3)} style={{ padding: "10px 24px", background: "linear-gradient(135deg, #3b82f6, #2563eb)", color: "#fff", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer" }}>Continuar →</button>
          </div>
        </div>
      )}

      {/* STEP 3: DATOS CLIENTE */}
      {step === 3 && (
        <div style={{ maxWidth: 550 }}>
          <h2 style={{ color: "#f1f5f9", fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Datos del cliente</h2>
          <p style={{ color: "#64748b", fontSize: 14, marginBottom: 28 }}>Completá los datos para la cotización</p>

          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {[
              { label: "Nombre / Razón social", value: clienteNombre, set: setClienteNombre, ph: "Ej: Agro del Sur S.A." },
              { label: "Contacto", value: clienteContacto, set: setClienteContacto, ph: "Ej: Juan Pérez - 351-555-1234" },
            ].map((f, i) => (
              <div key={i}>
                <label style={{ color: "#94a3b8", fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px", display: "block", marginBottom: 8 }}>{f.label}</label>
                <input value={f.value} onChange={e => f.set(e.target.value)} placeholder={f.ph}
                  style={{ width: "100%", padding: "14px 16px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, color: "#f1f5f9", fontSize: 14, outline: "none", boxSizing: "border-box" }} />
              </div>
            ))}

            <div>
              <label style={{ color: "#94a3b8", fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px", display: "block", marginBottom: 8 }}>Bonificación (%)</label>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <input type="range" min="0" max={empresa.bonif_max_porcentaje} step="0.5" value={bonificacion} onChange={e => setBonificacion(parseFloat(e.target.value))}
                  style={{ flex: 1, accentColor: "#3b82f6" }} />
                <span style={{ color: "#60a5fa", fontSize: 18, fontWeight: 700, minWidth: 50, textAlign: "right" }}>{bonificacion}%</span>
              </div>
              <span style={{ color: "#64748b", fontSize: 11 }}>Máximo permitido: {empresa.bonif_max_porcentaje}%</span>
            </div>

            <div>
              <label style={{ color: "#94a3b8", fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px", display: "block", marginBottom: 8 }}>Notas / Observaciones</label>
              <textarea value={notas} onChange={e => setNotas(e.target.value)} rows={3} placeholder="Notas adicionales para la cotización..."
                style={{ width: "100%", padding: "14px 16px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, color: "#f1f5f9", fontSize: 14, outline: "none", boxSizing: "border-box", resize: "vertical", fontFamily: "inherit" }} />
            </div>
          </div>

          <div style={{ display: "flex", gap: 12, marginTop: 28 }}>
            <button onClick={() => setStep(2)} style={{ padding: "10px 20px", background: "transparent", color: "#94a3b8", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 13, cursor: "pointer" }}>← Volver</button>
            <button onClick={() => setStep(4)} disabled={!clienteNombre.trim()} style={{ padding: "10px 24px", background: clienteNombre.trim() ? "linear-gradient(135deg, #3b82f6, #2563eb)" : "rgba(255,255,255,0.05)", color: clienteNombre.trim() ? "#fff" : "#64748b", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: clienteNombre.trim() ? "pointer" : "default" }}>Ver resumen →</button>
          </div>
        </div>
      )}

      {/* STEP 4: RESUMEN FINAL */}
      {step === 4 && (
        <div style={{ maxWidth: 650 }}>
          <h2 style={{ color: "#f1f5f9", fontSize: 22, fontWeight: 700, marginBottom: 24 }}>Resumen de cotización</h2>

          <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 16, padding: "28px", marginBottom: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20 }}>
              <div>
                <div style={{ color: "#64748b", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.5px" }}>Cliente</div>
                <div style={{ color: "#f1f5f9", fontSize: 16, fontWeight: 600, marginTop: 4 }}>{clienteNombre}</div>
                {clienteContacto && <div style={{ color: "#94a3b8", fontSize: 13, marginTop: 2 }}>{clienteContacto}</div>}
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ color: "#64748b", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.5px" }}>Implemento</div>
                <div style={{ color: "#f1f5f9", fontSize: 16, fontWeight: 600, marginTop: 4 }}>{producto?.nombre}</div>
                <div style={{ color: "#94a3b8", fontSize: 13, marginTop: 2 }}>{categoria?.nombre}</div>
              </div>
            </div>

            <div style={{ height: 1, background: "rgba(255,255,255,0.06)", margin: "0 0 20px" }} />

            {/* DESGLOSE */}
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "#94a3b8", fontSize: 14 }}>Precio base — {producto?.nombre}</span>
                <span style={{ color: "#e2e8f0", fontSize: 14 }}>{fmt(precioBase, empresa.simbolo)}</span>
              </div>

              {gruposDisponibles.map(g => {
                const val = selecciones[g.grupo_id];
                if (!val) return null;
                const items = g.tipo_seleccion === "unico" ? [val] : val;
                return items.map(oid => {
                  const opc = DB.opcionales.find(o => o.opcional_id === oid);
                  if (!opc || opc.precio === 0) return null;
                  return (
                    <div key={oid} style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: "#94a3b8", fontSize: 14, paddingLeft: 12 }}>+ {opc.nombre}</span>
                      <span style={{ color: "#e2e8f0", fontSize: 14 }}>{fmt(opc.precio, empresa.simbolo)}</span>
                    </div>
                  );
                });
              })}

              <div style={{ height: 1, background: "rgba(255,255,255,0.06)", margin: "4px 0" }} />

              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "#cbd5e1", fontSize: 14, fontWeight: 500 }}>Subtotal</span>
                <span style={{ color: "#e2e8f0", fontSize: 14, fontWeight: 500 }}>{fmt(subtotal, empresa.simbolo)}</span>
              </div>

              {bonificacion > 0 && (
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "#22c55e", fontSize: 14 }}>Bonificación ({bonificacion}%)</span>
                  <span style={{ color: "#22c55e", fontSize: 14 }}>-{fmt(bonifMonto, empresa.simbolo)}</span>
                </div>
              )}

              {bonificacion > 0 && (
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "#cbd5e1", fontSize: 14, fontWeight: 500 }}>Subtotal bonificado</span>
                  <span style={{ color: "#e2e8f0", fontSize: 14, fontWeight: 500 }}>{fmt(subtotalBonif, empresa.simbolo)}</span>
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "#94a3b8", fontSize: 14 }}>IVA ({empresa.iva_porcentaje}%)</span>
                <span style={{ color: "#e2e8f0", fontSize: 14 }}>{fmt(ivaMonto, empresa.simbolo)}</span>
              </div>

              <div style={{ height: 1, background: "rgba(59,130,246,0.3)", margin: "4px 0" }} />

              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0" }}>
                <span style={{ color: "#f1f5f9", fontSize: 20, fontWeight: 700 }}>TOTAL</span>
                <span style={{ color: "#60a5fa", fontSize: 22, fontWeight: 700 }}>{fmt(totalFinal, empresa.simbolo)}</span>
              </div>
            </div>
          </div>

          <div style={{ display: "flex", gap: 12 }}>
            <button onClick={() => setStep(3)} style={{ padding: "12px 20px", background: "transparent", color: "#94a3b8", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 13, cursor: "pointer" }}>← Volver</button>
            <button onClick={handleSave} style={{ padding: "12px 28px", background: "linear-gradient(135deg, #22c55e, #16a34a)", color: "#fff", border: "none", borderRadius: 8, fontSize: 14, fontWeight: 600, cursor: "pointer", flex: 1 }}>✓ Generar cotización</button>
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================
// HISTORIAL
// ============================================================
const Historial = ({ empresa, user }) => {
  const [pdfUri, setPdfUri] = useState(null);
  const [pdfCotId, setPdfCotId] = useState(null);
  const cots = user.rol === "vendedor"
    ? DB.cotizaciones.filter(c => c.empresa_id === empresa.empresa_id && c.usuario_id === user.usuario_id)
    : DB.cotizaciones.filter(c => c.empresa_id === empresa.empresa_id);

  if (cots.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: "80px 20px" }}>
        <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.5 }}>📋</div>
        <h3 style={{ color: "#94a3b8", fontWeight: 500 }}>No hay cotizaciones aún</h3>
        <p style={{ color: "#64748b", fontSize: 14 }}>Las cotizaciones generadas aparecerán acá</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 950, margin: "0 auto", padding: "32px 20px" }}>
      {pdfUri && <PDFPreview dataUri={pdfUri} cotId={pdfCotId} onClose={() => { setPdfUri(null); setPdfCotId(null); }} />}
      <h2 style={{ color: "#f1f5f9", fontSize: 22, fontWeight: 700, marginBottom: 24 }}>Historial de cotizaciones</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {cots.map(c => (
          <div key={c.cotizacion_id} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 14, padding: "20px 24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", gap: 28, alignItems: "center" }}>
              <div>
                <span style={{ color: "#60a5fa", fontSize: 13, fontWeight: 600 }}>{c.cotizacion_id}</span>
                <div style={{ color: "#f1f5f9", fontSize: 15, fontWeight: 500, marginTop: 2 }}>{c.cliente_nombre}</div>
              </div>
              <div>
                <div style={{ color: "#94a3b8", fontSize: 12 }}>{c.producto_nombre}</div>
                <div style={{ color: "#64748b", fontSize: 12, marginTop: 2 }}>{c.fecha} · {c.usuario_nombre}</div>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
              <div style={{ textAlign: "right" }}>
                <div style={{ color: "#f1f5f9", fontSize: 17, fontWeight: 700 }}>{fmt(c.total_final, empresa.simbolo)}</div>
                <span style={{ color: "#22c55e", fontSize: 11, background: "rgba(34,197,94,0.1)", padding: "3px 8px", borderRadius: 4 }}>{c.estado}</span>
              </div>
              <button onClick={async () => { const uri = await generatePDF(c, empresa); setPdfUri(uri); setPdfCotId(c.cotizacion_id); }}
                style={{ padding: "8px 14px", background: "rgba(34,197,94,0.1)", color: "#22c55e", border: "1px solid rgba(34,197,94,0.2)", borderRadius: 8, fontSize: 12, cursor: "pointer", fontWeight: 500, display: "flex", alignItems: "center", gap: 5, whiteSpace: "nowrap" }}
                onMouseOver={e => e.currentTarget.style.background = "rgba(34,197,94,0.2)"}
                onMouseOut={e => e.currentTarget.style.background = "rgba(34,197,94,0.1)"}>
                📄 PDF
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ============================================================
// ADMIN PANEL - EDITAR PRECIOS
// ============================================================
const AdminPanel = ({ empresa }) => {
  const [tab, setTab] = useState("productos");
  const [editingId, setEditingId] = useState(null);
  const [editValue, setEditValue] = useState("");
  const [toast, setToast] = useState("");

  const productos = DB.productos.filter(p => p.empresa_id === empresa.empresa_id);
  const opcionales = DB.opcionales.filter(o => o.empresa_id === empresa.empresa_id);

  const savePrice = (type, id, newPrice) => {
    const num = parseFloat(newPrice);
    if (isNaN(num) || num < 0) return;
    if (type === "producto") {
      const p = DB.productos.find(x => x.producto_id === id);
      if (p) p.precio_base = num;
    } else {
      const o = DB.opcionales.find(x => x.opcional_id === id);
      if (o) o.precio = num;
    }
    setEditingId(null);
    setEditValue("");
    setToast("Precio actualizado correctamente");
    setTimeout(() => setToast(""), 2500);
  };

  const tabs = [
    { id: "productos", label: "Productos", icon: "📦" },
    { id: "opcionales", label: "Opcionales", icon: "🔧" },
    { id: "config", label: "Configuración", icon: "⚙️" },
  ];

  return (
    <div style={{ maxWidth: 950, margin: "0 auto", padding: "32px 20px" }}>
      <h2 style={{ color: "#f1f5f9", fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Administrar precios</h2>
      <p style={{ color: "#64748b", fontSize: 14, marginBottom: 24 }}>Editá los precios y el sistema los usa automáticamente en las nuevas cotizaciones</p>

      {toast && (
        <div style={{ position: "fixed", top: 76, right: 28, background: "rgba(34,197,94,0.15)", border: "1px solid rgba(34,197,94,0.3)", color: "#22c55e", padding: "12px 20px", borderRadius: 10, fontSize: 13, fontWeight: 500, zIndex: 200, animation: "fadeIn 0.3s" }}>✓ {toast}</div>
      )}

      <div style={{ display: "flex", gap: 6, marginBottom: 28 }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            style={{ padding: "10px 20px", background: tab === t.id ? "rgba(59,130,246,0.15)" : "transparent", color: tab === t.id ? "#60a5fa" : "#94a3b8", border: tab === t.id ? "1px solid rgba(59,130,246,0.3)" : "1px solid rgba(255,255,255,0.06)", borderRadius: 8, fontSize: 13, cursor: "pointer", fontWeight: tab === t.id ? 600 : 400, display: "flex", alignItems: "center", gap: 6 }}>
            <span>{t.icon}</span>{t.label}
          </button>
        ))}
      </div>

      {tab === "productos" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 180px 120px", gap: 16, padding: "12px 20px", background: "rgba(255,255,255,0.02)", borderRadius: 8 }}>
            <span style={{ color: "#64748b", fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>Producto</span>
            <span style={{ color: "#64748b", fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px", textAlign: "right" }}>Precio base</span>
            <span style={{ color: "#64748b", fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px", textAlign: "center" }}>Acción</span>
          </div>
          {productos.map(p => {
            const isEditing = editingId === p.producto_id;
            return (
              <div key={p.producto_id} style={{ display: "grid", gridTemplateColumns: "1fr 180px 120px", gap: 16, padding: "14px 20px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 10, alignItems: "center" }}>
                <div>
                  <span style={{ color: "#f1f5f9", fontSize: 14, fontWeight: 500 }}>{p.nombre}</span>
                  <span style={{ color: "#64748b", fontSize: 12, marginLeft: 8 }}>{p.producto_id}</span>
                </div>
                {isEditing ? (
                  <input autoFocus value={editValue} onChange={e => setEditValue(e.target.value)}
                    onKeyDown={e => { if (e.key === "Enter") savePrice("producto", p.producto_id, editValue); if (e.key === "Escape") setEditingId(null); }}
                    style={{ padding: "8px 12px", background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.4)", borderRadius: 8, color: "#f1f5f9", fontSize: 14, textAlign: "right", outline: "none", width: "100%", boxSizing: "border-box" }} />
                ) : (
                  <span style={{ color: "#e2e8f0", fontSize: 15, fontWeight: 600, textAlign: "right" }}>{fmt(p.precio_base, empresa.simbolo)}</span>
                )}
                <div style={{ textAlign: "center" }}>
                  {isEditing ? (
                    <div style={{ display: "flex", gap: 6, justifyContent: "center" }}>
                      <button onClick={() => savePrice("producto", p.producto_id, editValue)} style={{ padding: "6px 12px", background: "rgba(34,197,94,0.15)", color: "#22c55e", border: "1px solid rgba(34,197,94,0.3)", borderRadius: 6, fontSize: 12, cursor: "pointer" }}>✓</button>
                      <button onClick={() => setEditingId(null)} style={{ padding: "6px 12px", background: "rgba(239,68,68,0.1)", color: "#f87171", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 6, fontSize: 12, cursor: "pointer" }}>✕</button>
                    </div>
                  ) : (
                    <button onClick={() => { setEditingId(p.producto_id); setEditValue(String(p.precio_base)); }}
                      style={{ padding: "6px 16px", background: "rgba(59,130,246,0.1)", color: "#60a5fa", border: "1px solid rgba(59,130,246,0.2)", borderRadius: 6, fontSize: 12, cursor: "pointer" }}>Editar</button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {tab === "opcionales" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 140px 180px 120px", gap: 12, padding: "12px 20px", background: "rgba(255,255,255,0.02)", borderRadius: 8 }}>
            <span style={{ color: "#64748b", fontSize: 12, fontWeight: 600, textTransform: "uppercase" }}>Opcional</span>
            <span style={{ color: "#64748b", fontSize: 12, fontWeight: 600, textTransform: "uppercase" }}>Grupo</span>
            <span style={{ color: "#64748b", fontSize: 12, fontWeight: 600, textTransform: "uppercase", textAlign: "right" }}>Precio</span>
            <span style={{ color: "#64748b", fontSize: 12, fontWeight: 600, textTransform: "uppercase", textAlign: "center" }}>Acción</span>
          </div>
          {opcionales.map(o => {
            const grupo = DB.grupos.find(g => g.grupo_id === o.grupo_id);
            const isEditing = editingId === o.opcional_id;
            return (
              <div key={o.opcional_id} style={{ display: "grid", gridTemplateColumns: "1fr 140px 180px 120px", gap: 12, padding: "14px 20px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 10, alignItems: "center" }}>
                <span style={{ color: "#f1f5f9", fontSize: 14 }}>{o.nombre}</span>
                <span style={{ color: "#94a3b8", fontSize: 12, background: "rgba(255,255,255,0.05)", padding: "4px 8px", borderRadius: 4, textAlign: "center" }}>{grupo?.nombre || "-"}</span>
                {isEditing ? (
                  <input autoFocus value={editValue} onChange={e => setEditValue(e.target.value)}
                    onKeyDown={e => { if (e.key === "Enter") savePrice("opcional", o.opcional_id, editValue); if (e.key === "Escape") setEditingId(null); }}
                    style={{ padding: "8px 12px", background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.4)", borderRadius: 8, color: "#f1f5f9", fontSize: 14, textAlign: "right", outline: "none", width: "100%", boxSizing: "border-box" }} />
                ) : (
                  <span style={{ color: o.precio > 0 ? "#e2e8f0" : "#64748b", fontSize: 14, fontWeight: 500, textAlign: "right" }}>{o.precio > 0 ? fmt(o.precio, empresa.simbolo) : "Incluido"}</span>
                )}
                <div style={{ textAlign: "center" }}>
                  {isEditing ? (
                    <div style={{ display: "flex", gap: 6, justifyContent: "center" }}>
                      <button onClick={() => savePrice("opcional", o.opcional_id, editValue)} style={{ padding: "6px 12px", background: "rgba(34,197,94,0.15)", color: "#22c55e", border: "1px solid rgba(34,197,94,0.3)", borderRadius: 6, fontSize: 12, cursor: "pointer" }}>✓</button>
                      <button onClick={() => setEditingId(null)} style={{ padding: "6px 12px", background: "rgba(239,68,68,0.1)", color: "#f87171", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 6, fontSize: 12, cursor: "pointer" }}>✕</button>
                    </div>
                  ) : (
                    <button onClick={() => { setEditingId(o.opcional_id); setEditValue(String(o.precio)); }}
                      style={{ padding: "6px 16px", background: "rgba(59,130,246,0.1)", color: "#60a5fa", border: "1px solid rgba(59,130,246,0.2)", borderRadius: 6, fontSize: 12, cursor: "pointer" }}>Editar</button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {tab === "config" && (
        <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 14, padding: "24px" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {[
              { label: "IVA (%)", value: empresa.iva_porcentaje, key: "iva" },
              { label: "Bonificación máxima (%)", value: empresa.bonif_max_porcentaje, key: "bonif" },
              { label: "Moneda", value: empresa.moneda, key: "moneda" },
            ].map(c => (
              <div key={c.key} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 0", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                <span style={{ color: "#94a3b8", fontSize: 14 }}>{c.label}</span>
                <span style={{ color: "#f1f5f9", fontSize: 16, fontWeight: 600 }}>{c.value}</span>
              </div>
            ))}
          </div>
          <p style={{ color: "#64748b", fontSize: 12, marginTop: 20, fontStyle: "italic" }}>En producción, estos valores se editan directamente desde acá y se guardan en Google Sheets.</p>
        </div>
      )}
    </div>
  );
};

// ============================================================
// APP PRINCIPAL
// ============================================================
export default function App() {
  const [user, setUser] = useState(null);
  const [view, setView] = useState("cotizar");

  if (!user) return <LoginScreen onLogin={(u) => { setUser(u); setView("cotizar"); }} />;

  const empresa = DB.empresas.find(e => e.empresa_id === user.empresa_id);

  return (
    <div style={{ minHeight: "100vh", background: "linear-gradient(180deg, #0f172a 0%, #131c2e 100%)", fontFamily: "'DM Sans', system-ui, sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />
      <TopBar user={user} empresa={empresa} currentView={view} onNavigate={setView} onLogout={() => setUser(null)} />
      {view === "cotizar" && <CotizadorWizard empresa={empresa} user={user} />}
      {view === "historial" && <Historial empresa={empresa} user={user} />}
      {view === "admin" && <AdminPanel empresa={empresa} />}
    </div>
  );
}
