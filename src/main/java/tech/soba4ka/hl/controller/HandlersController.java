package tech.soba4ka.hl.controller;

import java.util.Comparator;
import java.util.List;
import java.util.Set;

import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.RequestMappingHandlerMapping;
import tech.soba4ka.hl.dto.HandlerResponse;

@RestController
@RequiredArgsConstructor
public class HandlersController {
    private static final Set<String> SERVICE_PATHS = Set.of("/health", "/metrics", "/handlers", "/error");
    @Qualifier("requestMappingHandlerMapping")
    private final RequestMappingHandlerMapping mappings;

    @GetMapping("/handlers")
    public List<HandlerResponse> handlers() {
        return mappings.getHandlerMethods().keySet().stream()
                .flatMap(mapping -> mapping.getPatternValues().stream()
                        .filter(path -> !SERVICE_PATHS.contains(path))
                        .flatMap(path -> mapping.getMethodsCondition().getMethods().stream()
                                .map(method -> new HandlerResponse(method.name(), path))))
                .distinct()
                .sorted(Comparator.comparing(HandlerResponse::path).thenComparing(HandlerResponse::method))
                .toList();
    }
}
