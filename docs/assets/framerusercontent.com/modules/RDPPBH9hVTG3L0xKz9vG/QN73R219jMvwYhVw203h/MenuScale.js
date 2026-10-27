let r;
var f = (e) => {
    if (!r) {
        let o = function(n, t) {
            return e.createElement("svg", {width: "100%", height: "1.5em", strokeWidth: 1.5, viewBox: "0 0 24 24", fill: "none", xmlns: "http://www.w3.org/2000/svg", color: "currentColor", ref: t, ...n}, e.createElement("path", {d: "M3 5h8M3 12h13M3 19h18", stroke: "currentColor", strokeLinecap: "round", strokeLinejoin: "round"}));
        };
        r = e.forwardRef(o);
    }
    return r;
};
const __FramerMetadata__ = {exports: {default: {type: "reactComponent", slots: [], annotations: {framerContractVersion: "1"}}, __FramerMetadata__: {type: "variable"}}};
export { __FramerMetadata__, f as default };