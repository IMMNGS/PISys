import { Link } from "react-router-dom";

export default function Home() {
  const cards = [
    {
      title: "Patients",
      icon: "👥",
      desc: "Search, filter and export",
      link: "/select",
    },
    {
      title: "Upload",
      icon: "📤",
      desc: "Import VCF and spreadsheets",
      link: "/upload",
    },
    {
      title: "Report",
      icon: "📄",
      desc: "Generate clinical report",
      link: "/report",
    },
    {
      title: "Disease Terms",
      icon: "🏷️",
      desc: "Manage and assign terms",
      link: "/manage-hpo",
    },
    {
      title: "Statistics",
      icon: "📊",
      desc: "View descriptive stats",
      link: "/stats",
    },
    {
      title: "Admin",
      icon: "🛡️",
      desc: "Audit and user management",
      link: "/admin",
    },
  ];

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#f1f5f9",
        paddingTop: "3rem",
        paddingBottom: "2rem",
      }}
    >
      <div className="text-center">
        <h1
          style={{
            fontSize: "2.5rem",
            fontWeight: 700,
            marginBottom: "0.5rem",
            color: "#1a1a1a",
          }}
        >
          Patient Information System
        </h1>
        <p
          style={{
            fontSize: "1rem",
            color: "#666",
            marginBottom: "2rem",
            maxWidth: "560px",
            marginLeft: "auto",
            marginRight: "auto",
          }}
        >
          Manage patients, uploads, reports, and terms in one place
        </p>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))",
            gap: "1rem",
            maxWidth: "980px",
            marginLeft: "auto",
            marginRight: "auto",
            padding: "0 1rem",
          }}
        >
          {cards.map((card) => (
            <Link
              key={card.link}
              to={card.link}
              style={{ textDecoration: "none" }}
            >
              <div
                style={{
                  background: "#ffffff",
                  borderRadius: "12px",
                  padding: "1.25rem 1rem",
                  minHeight: "120px",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  transition: "all 0.2s ease",
                  boxShadow: "0 2px 10px rgba(0,0,0,0.08)",
                  border: "1px solid #ececec",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = "translateY(-4px)";
                  e.currentTarget.style.boxShadow =
                    "0 8px 18px rgba(0,0,0,0.12)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = "translateY(0)";
                  e.currentTarget.style.boxShadow =
                    "0 2px 10px rgba(0,0,0,0.08)";
                }}
              >
                <div
                  style={{
                    width: "44px",
                    height: "44px",
                    borderRadius: "50%",
                    background: "#eef2ff",
                    border: "1px solid #c7d2fe",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#3730a3",
                    fontSize: "1.2rem",
                    lineHeight: 1,
                    marginBottom: "0.65rem",
                  }}
                >
                  {card.icon}
                </div>
                <h3
                  style={{
                    fontSize: "1.1rem",
                    fontWeight: 600,
                    color: "#222",
                    margin: "0 0 0.4rem 0",
                  }}
                >
                  {card.title}
                </h3>
                <p style={{ fontSize: "0.9rem", color: "#666", margin: 0 }}>
                  {card.desc}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
