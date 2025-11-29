import React from 'react';

export default function GovBar() {
    React.useEffect(() => {
        const scriptId = 'govbr-barra-script';
        // Evita adicionar o script múltiplas vezes
    if (document.getElementById(scriptId)) {
        return;
    }

    const script = document.createElement("script");
    script.id = scriptId;
    script.src = "https://barra.brasil.gov.br/barra_2.0.js";
    script.async = true;
    document.head.appendChild(script);

    return () => {
        const scriptElement = document.getElementById(scriptId);
        if (scriptElement && scriptElement.parentNode) {
            scriptElement.parentNode.removeChild(scriptElement);
        }
    };
    }, []);

    return (
        <div id="barra-brasil" style={{ background: 'transparent', display: 'block' }}>
        {/* O conteúdo da barra é injetado pelo script do governo. */}
        </div>
    );
}
