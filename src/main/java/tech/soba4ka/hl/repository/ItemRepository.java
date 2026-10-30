package tech.soba4ka.hl.repository;

import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

import org.springframework.stereotype.Repository;
import tech.soba4ka.hl.dto.ItemRequest;
import tech.soba4ka.hl.model.Item;

@Repository
public class ItemRepository {
    private final ConcurrentHashMap<Long, Item> items = new ConcurrentHashMap<>();
    private final AtomicLong sequence = new AtomicLong();

    public Item create(ItemRequest request) {
        long id = sequence.incrementAndGet();
        Item item = new Item(id, request.name(), request.description());
        items.put(id, item);
        return item;
    }

    public Optional<Item> find(long id) {
        return Optional.ofNullable(items.get(id));
    }

    public Optional<Item> update(long id, ItemRequest request) {
        return Optional.ofNullable(items.computeIfPresent(id,
                (key, previous) -> new Item(key, request.name(), request.description())));
    }
}
